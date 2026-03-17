/**
 * Session Journal Hook — comprehensive anti-compaction system.
 *
 * This hook is the ONLY anti-compaction mechanism needed (no LCM required).
 *
 * Listens to:
 * - message:received / message:sent → captures every message to journal
 * - session:compact:before → forces full save before compaction
 *
 * Every SUMMARY_INTERVAL messages:
 * 1. Summarizes the journal → .session_snapshot.md
 * 2. Updates CURRENT.md (micro-state)
 *
 * On compact:before:
 * 1. Forces immediate summarization
 * 2. Forces CURRENT.md update
 * 3. Logs the compaction event
 */

import { appendFileSync, writeFileSync, readFileSync, existsSync } from "fs";
import { join } from "path";
import { execFile } from "child_process";

const sessionMessageCounts: Map<string, number> = new Map();
let lastSummaryTime: number = 0;

const handler = async (event: any) => {
  // --- Handle compact:before (critical save before compaction) ---
  if (event.type === "session" && event.action === "compact:before") {
    const workspaceDir = event.context?.workspaceDir;
    if (!workspaceDir) return;

    console.log("[session-journal] compact:before detected — forcing full save");

    const journalPath = join(workspaceDir, ".session_journal.jsonl");
    const snapshotPath = join(workspaceDir, ".session_snapshot.md");

    // Log the compaction event
    try {
      const entry = JSON.stringify({
        ts: new Date().toISOString(),
        role: "system",
        session: event.sessionKey || "unknown",
        content: "[COMPACTION] Context about to be compacted",
      });
      appendFileSync(journalPath, entry + "\n", "utf-8");
    } catch (err) {
      console.error(`[session-journal] Failed to log compaction: ${err}`);
    }

    // CURRENT.md FIRST (< 100ms, no LLM, guaranteed fast)
    await triggerCurrentUpdate(workspaceDir, journalPath);

    // THEN summarization (may take up to 10s, has raw fallback if timeout)
    await triggerSummarization(workspaceDir, journalPath, snapshotPath, true);

    event.messages?.push("📓 Session saved before compaction");
    return;
  }

  // --- Handle messages ---
  if (event.type !== "message") return;
  if (event.action !== "received" && event.action !== "sent") return;

  const workspaceDir = event.context?.workspaceDir;
  if (!workspaceDir) return;

  const journalPath = join(workspaceDir, ".session_journal.jsonl");
  const snapshotPath = join(workspaceDir, ".session_snapshot.md");
  const sessionKey = event.sessionKey || "default";

  // Extract message content
  let content = "";
  let role = "unknown";

  if (event.action === "received") {
    content = event.context?.content || "";
    role = "user";
  } else if (event.action === "sent") {
    content = event.context?.content || "";
    role = "assistant";
    if (!content || content.trim() === "NO_REPLY") return;
  }

  if (!content || content.length < 2) return;

  // Truncate very long messages
  const maxLen = 1000;
  const truncated = content.length > maxLen ? content.substring(0, maxLen) + "..." : content;

  // Append to journal
  const entry = JSON.stringify({
    ts: new Date().toISOString(),
    role,
    session: sessionKey,
    content: truncated,
  });

  try {
    appendFileSync(journalPath, entry + "\n", "utf-8");
  } catch (err) {
    console.error(`[session-journal] Failed to write journal: ${err}`);
    return;
  }

  // Count messages
  const count = (sessionMessageCounts.get(sessionKey) || 0) + 1;
  sessionMessageCounts.set(sessionKey, count);

  // Trigger summarization every N messages
  const interval = parseInt(process.env.SUMMARY_INTERVAL || "10", 10);
  if (count % interval === 0) {
    await triggerSummarization(workspaceDir, journalPath, snapshotPath, false);
  }

  // Update CURRENT.md every 5 messages (lightweight, no LLM call)
  if (count % 5 === 0) {
    await triggerCurrentUpdate(workspaceDir, journalPath);
  }
};

async function triggerSummarization(
  workspaceDir: string,
  journalPath: string,
  snapshotPath: string,
  urgent: boolean
): Promise<void> {
  // Rate limit: don't summarize more than once per 2 minutes (unless urgent/compact:before)
  const now = Date.now();
  if (!urgent && now - lastSummaryTime < 120_000) return;
  lastSummaryTime = now;

  // Skip if less than 3 messages in journal (not worth summarizing)
  try {
    const journalContent = readFileSync(journalPath, "utf-8");
    const lineCount = journalContent.split("\n").filter(l => l.trim()).length;
    if (lineCount < 3 && !urgent) return;
  } catch { /* file may not exist yet */ }

  const provider = process.env.SUMMARY_PROVIDER || "google";
  const model = process.env.SUMMARY_MODEL || "";
  const scriptDir = findScriptDir(workspaceDir);

  if (!scriptDir) {
    console.error("[session-journal] Could not find memory_session_summary.py");
    // Fallback: write raw last messages as snapshot if urgent
    if (urgent) {
      try {
        const raw = readFileSync(journalPath, "utf-8");
        const lines = raw.split("\n").filter(l => l.trim()).slice(-10);
        const fallback = `<!-- FALLBACK: LLM summarization failed, raw messages -->\n# Session Snapshot (raw)\n\n${lines.map(l => {
          try { const m = JSON.parse(l); return \`- \${m.role}: \${m.content?.substring(0, 200)}\`; } catch { return ""; }
        }).filter(Boolean).join("\n")}\n`;
        writeFileSync(snapshotPath, fallback, "utf-8");
        console.log("[session-journal] Wrote raw fallback snapshot");
      } catch (e) {
        console.error(`[session-journal] Fallback snapshot failed: ${e}`);
      }
    }
    return;
  }

  const scriptPath = join(scriptDir, "memory_session_summary.py");
  const args = [
    scriptPath,
    "--journal", journalPath,
    "--snapshot", snapshotPath,
    "--provider", provider,
    "--keep-recent", "5",
  ];

  if (model) args.push("--model", model);

  // For urgent (compact:before), use shorter timeout (10s) and try fallback on failure
  const timeout = urgent ? 10_000 : 60_000;
  const label = urgent ? "URGENT (compact:before)" : "periodic";
  console.log(`[session-journal] Summarization ${label} — ${provider} (timeout: ${timeout}ms)`);

  return new Promise<void>((resolve) => {
    execFile("python3", args, {
      timeout,
      env: { ...process.env },
    }, (error, stdout, stderr) => {
      if (error) {
        console.error(`[session-journal] Summarization failed: ${error.message}`);
        // On urgent failure: write raw fallback
        if (urgent) {
          try {
            const raw = readFileSync(journalPath, "utf-8");
            const lines = raw.split("\n").filter(l => l.trim()).slice(-10);
            const fallback = `<!-- FALLBACK: LLM timeout, raw messages preserved -->\n# Session Snapshot (raw)\n\n${lines.map(l => {
              try { const m = JSON.parse(l); return \`- \${m.role}: \${m.content?.substring(0, 200)}\`; } catch { return ""; }
            }).filter(Boolean).join("\n")}\n`;
            writeFileSync(snapshotPath, fallback, "utf-8");
            console.log("[session-journal] Wrote raw fallback snapshot (LLM timeout)");
          } catch (e) {
            console.error(`[session-journal] Fallback failed: ${e}`);
          }
        }
      } else {
        console.log(`[session-journal] ${stdout.trim()}`);
      }
      resolve();
    });
  });
}

async function triggerCurrentUpdate(
  workspaceDir: string,
  journalPath: string
): Promise<void> {
  const scriptDir = findScriptDir(workspaceDir);
  if (!scriptDir) return;

  const scriptPath = join(scriptDir, "memory_current.py");
  const dbPath = join(workspaceDir, "memory.db");
  const outputPath = join(workspaceDir, "CURRENT.md");

  execFile("python3", [
    scriptPath,
    "--from-journal", journalPath,
    "--db", dbPath,
    "--output", outputPath,
  ], {
    timeout: 10_000,
    env: { ...process.env },
  }, (error, stdout, stderr) => {
    if (error) {
      console.error(`[session-journal] CURRENT.md update failed: ${error.message}`);
    }
  });
}

function findScriptDir(workspaceDir: string): string | null {
  const candidates = [
    join(workspaceDir, "skills", "persistent-memory", "scripts"),
    join(workspaceDir, "skills", "companion", "scripts"),
    join(workspaceDir, "skills", "romantic-companion", "scripts"),
    join(process.env.HOME || "~", ".openclaw", "skills", "persistent-memory", "scripts"),
    join(process.env.HOME || "~", ".openclaw", "skills", "companion", "scripts"),
    join(process.env.HOME || "~", ".openclaw", "skills", "romantic-companion", "scripts"),
  ];

  for (const dir of candidates) {
    if (existsSync(join(dir, "memory_session_summary.py"))) {
      return dir;
    }
  }

  return null;
}

export default handler;
