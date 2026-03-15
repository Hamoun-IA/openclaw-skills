# Image Prompt Templates

Templates for generating companion images. The agent customizes these based on context.

## Prompt Structure

```
[Person description from reference] + [Activity/Scene] + [Lighting/Time] + [Season/Weather] + [Mood/Expression]
```

## Selfie Prompts

### Morning
- "A [person] taking a selfie just waking up, soft morning light, messy hair, sleepy smile, bedroom"
- "A [person] holding a coffee mug, kitchen, natural light from window, cozy morning"
- "A [person] doing yoga on a mat, morning light, focused expression, peaceful room"

### Midday
- "A [person] taking a selfie at a café terrace, midday light, casual outfit, smiling"
- "A [person] at a restaurant, nice lunch plate in front, natural light"

### Evening
- "A [person] taking a selfie on a couch, warm lamp light, relaxed, cozy evening"
- "A [person] in a kitchen cooking, warm lighting, apron, happy expression"

### Night
- "A [person] in bed, dim light, sleepy, peaceful expression, night"
- "A [person] holding a cup of tea, dark window behind, calm expression"

## Food Prompts (no person needed)
- "Overhead photo of a beautiful [meal] on a wooden table, natural light, restaurant"
- "A homemade [meal] on a plate, kitchen counter, cozy lighting, steam rising"

## Scenery Prompts (no person needed)
- "A beautiful [season] view from a café window, [weather], ambient"
- "A sunset over [city], warm colors, peaceful"
- "A cozy reading corner with a book and [hot drink], [season] mood"

## Key Guidelines

1. **Always specify lighting** matching the time of day
2. **Always specify season** matching the real calendar
3. **Keep the same style** — photorealistic, natural, not posed
4. **Expressions should be natural** — not exaggerated smiles
5. **Clothing should match** season and activity
6. **Include the reference instruction** when using a face reference:
   "Generate an image of this exact person in the following scene. Maintain face identity from the reference photo."
