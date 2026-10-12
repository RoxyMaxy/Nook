/* Nook Local Vision AI — runs in the browser, no Ollama or Python model server.
 * The compact SmolVLM model is downloaded once, then Transformers.js browser cache
 * can reuse its files offline. First setup requires a connection and enough storage.
 */
(() => {
  'use strict';
  const MODEL_ID = 'HuggingFaceTB/SmolVLM-256M-Instruct';
  let extractorPromise = null;
  let transformersPromise = null;

  async function loadPipeline(onProgress) {
    if (extractorPromise) return extractorPromise;
    extractorPromise = (async () => {
      onProgress?.('Loading browser inference engine…');
      // Keep the runtime and model in the browser cache for later offline use.
      const { pipeline, env } = await import('https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.7.2');
      env.useBrowserCache = true;
      env.allowRemoteModels = true;
      env.allowLocalModels = false;
      onProgress?.('Preparing compact vision model (first run needs Internet)…');
      return pipeline('image-text-to-text', MODEL_ID, {
        dtype: 'q4',
        progress_callback: (event) => {
          if (event?.status === 'progress' && Number.isFinite(event.progress)) {
            onProgress?.(`Downloading model: ${Math.round(event.progress)}%`);
          } else if (event?.status === 'ready') {
            onProgress?.('Local vision model ready.');
          }
        }
      });
    })().catch((error) => {
      extractorPromise = null;
      throw error;
    });
    return extractorPromise;
  }

  function dataUrlToBlob(dataUrl) {
    const [meta, data] = dataUrl.split(',');
    const mime = (meta.match(/data:([^;]+)/) || [])[1] || 'image/jpeg';
    const binary = atob(data);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return new Blob([bytes], { type: mime });
  }

  function parseNaturalistText(raw) {
    const text = String(raw || '').replace(/^\s*assistant\s*/i, '').trim();
    const section = (name, nextNames = []) => {
      const start = text.search(new RegExp(`(?:^|\\n)\\s*${name}\\s*:?\\s*`, 'i'));
      if (start < 0) return '';
      const after = text.slice(start).replace(new RegExp(`^(?:\\n)?\\s*${name}\\s*:?\\s*`, 'i'), '');
      let end = after.length;
      for (const next of nextNames) {
        const match = after.search(new RegExp(`\\n\\s*${next}\\s*:?\\s*`, 'i'));
        if (match >= 0) end = Math.min(end, match);
      }
      return after.slice(0, end).trim();
    };
  
    const id = section('IDENTIFICATION', ['VISIBLE DETAILS','HYPOTHESES','ALTERNATIVES','LIMITS','QUESTION','MISSION','CREATIVE IDEA']);
    const list = (value) => value.split(/\n|•|\s-\s/).map(s => s.replace(/^[-*\d.)\s]+/, '').trim()).filter(Boolean).slice(0, 5);
    const seen = list(section('VISIBLE DETAILS', ['HYPOTHESES','ALTERNATIVES','LIMITS','QUESTION','MISSION','CREATIVE IDEA']));
    const hypotheses = list(section('HYPOTHESES', ['ALTERNATIVES','LIMITS','QUESTION','MISSION','CREATIVE IDEA']));
    const alternatives = list(section('ALTERNATIVES', ['LIMITS','QUESTION','MISSION','CREATIVE IDEA']));
    const limits = section('LIMITS', ['QUESTION','MISSION','CREATIVE IDEA']);
    const question = section('QUESTION', ['MISSION','CREATIVE IDEA']);
    const mission = section('MISSION', ['CREATIVE IDEA']);
    const atelier = section('CREATIVE IDEA');
    // If the model ignores the requested headings, preserve its actual caption rather than inventing content.
    if (!seen.length) seen.push(text.slice(0, 700) || 'The model returned no description. Try another photo.');
    return {
      possible_identification: id || 'Possible identification needs closer comparison',
      seen,
      hypotheses: hypotheses.length ? hypotheses : ['The photo alone does not establish a cause or history.'],
      alternatives: alternatives.length ? alternatives : ['A second possibility cannot be proposed confidently from this image alone.'],
      uncertain: limits || 'Species, exact cause, and unseen environmental conditions may not be identifiable from this photo alone.',
      investigation_question: question || 'Which visible detail changes most when you compare this specimen with another nearby example?',
      observation_mission: mission || 'Observe one similar specimen nearby without picking, touching, or disturbing it.',
      atelier: atelier || 'Make a contour sketch from the photo, noting its visible patterns and shapes.',
      analysis_mode: 'local-browser',
      model: MODEL_ID
    };
  }

  async function analyze(imageDataUrl, onProgress) {
    const model = await loadPipeline(onProgress);
    onProgress?.('Examining visible details and forming cautious hypotheses…');
    const prompt = `You are Nook, a careful, friendly naturalist. Analyze THIS exact image, not a generic example. Do not assume it is a leaf. Use accessible scientific language. Never claim details not clearly visible; distinguish observation from hypothesis and uncertainty. Do not infer season, weather, location, damage cause, or species without evidence. Do not recommend touching, picking, scraping, or disturbing living organisms. Return these headings exactly, with concise content under each:
IDENTIFICATION: best tentative identification or broad object category, with confidence (low/medium/high) and a brief reason.
VISIBLE DETAILS: 3-5 details plainly visible in this image (shape, color, pattern, texture, edges, marks).
HYPOTHESES: 1-3 plausible explanations, explicitly marked as possibilities.
ALTERNATIVES: up to 2 alternatives only if plausible.
LIMITS: what cannot be determined from this image.
QUESTION: one useful question to train observation.
MISSION: one safe, non-invasive real-world observation task.
CREATIVE IDEA: one small creative activity based on this specific image, using the photo or reused/fallen materials. Never invent certainty. If the image is unclear, say so.`;
    const messages = [{ role: 'user', content: [{ type: 'image', url: imageDataUrl }, { type: 'text', text: prompt }] }];
    const output = await model(messages, { max_new_tokens: 320, do_sample: false, return_full_text: false });
    const result = Array.isArray(output) ? output[0] : output;
    const generated = result?.generated_text ?? result?.text ?? '';
    const raw = Array.isArray(generated) ? generated.map(part => part.text || '').join('\n') : String(generated);
    if (!raw.trim()) throw new Error('The local vision model returned an empty answer.');
    return parseNaturalistText(raw);
  }

  window.NookLocalAI = {
    modelId: MODEL_ID,
    analyze,
    isReady: () => Boolean(extractorPromise),
    clearFailedLoad: () => { extractorPromise = null; }
  };
})();
