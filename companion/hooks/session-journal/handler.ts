/**
 * Session Journal Hook — captures messages and triggers periodic summarization.
 *
 * Listens to message:received and message:sent events.
 * Appends each message to .session_journal.jsonl in the workspace.
 * Every SUMMARY_INTERVAL messages, runs memory_session_summary.py for external summarization.
 */

import { appendFileSync, readFileSync, existsSync } from "fs";
import { join } from "path";
import { execFile } from "child_process";

// Track message counts per session to know when to trigger summarization
const sessionMessageCounts: Map<string, number> = new Map();

const handler = async (event: any) => {
  // Only handle message events
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
    // Skip empty or NO_REPLY messages
    if (!content || content.trim() === "NO_REPLY") return;
  }

  if (!content || content.length < 2) return;

  // Truncate very long messages (tool outputs, etc.)
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

  // Count messages for this session
  const count = (sessionMessageCounts.get(sessionKey) || 0) + 1;
  sessionMessageCounts.set(sessionKey, count);

  // Check if we should trigger summarization
  const interval = parseInt(process.env.SUMMARY_INTERVAL || "10", 10);
  if (count % interval !== 0) return;

  // Trigger summarization asynchronously (fire and forget)
  const provider = process.env.SUMMARY_PROVIDER || "google";
  const model = process.env.SUMMARY_MODEL || "";
  const scriptDir = findScriptDir(workspaceDir);

  if (!scriptDir) {
    console.error("[session-journal] Could not find memory_session_summary.py");
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

  if (model) {
    args.push("--model", model);
  }

  console.log(`[session-journal] Triggering summarization (${count} messages, provider: ${provider})`);

  execFile("python3", args, {
    timeout: 60000,
    env: { ...process.env },
  }, (error, stdout, stderr) => {
    if (error) {
      console.error(`[session-journal] Summarization failed: ${error.message}`);
      if (stderr) console.error(`[session-journal] ${stderr}`);
    } else {
      console.log(`[session-journal] ${stdout.trim()}`);
    }
  });
};

/**
 * Find the persistent-memory scripts directory.
 * Checks common locations in order.
 */
function findScriptDir(workspaceDir: string): string | null {
  const candidates = [
    // Workspace-local skill
    join(workspaceDir, "skills", "persistent-memory", "scripts"),
    // Global skills
    join(process.env.HOME || "~", ".openclaw", "skills", "persistent-memory", "scripts"),
  ];

  for (const dir of candidates) {
    const scriptPath = join(dir, "memory_session_summary.py");
    if (existsSync(scriptPath)) {
      return dir;
    }
  }

  return null;
}

export default handler;
