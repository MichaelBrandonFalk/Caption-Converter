const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { loadBrowser } = require('./browser_harness.cjs');
const cases = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures/caption_cases.json'), 'utf8'));

for (const c of cases) {
  test(c.name, async () => {
    const browser = loadBrowser();
    const parse = c.format === 'srt' ? 'parseSrtCues' : 'parseVttCues';
    browser.call('handleFiles', [{ name: `captions.${c.format}`, text: async () => c.source }]);
    if (c.error) {
      await assert.rejects(browser.call('convertSelectedFile'), new RegExp(c.error));
      assert.equal(browser.elements.get('results').children.length, 0);
      // Exercise the normal click handler's alert flow, too.
      browser.elements.get('convert-button').listeners.click();
      await new Promise(setImmediate);
      assert.equal(browser.alerts.length, 1);
      assert.match(browser.alerts[0], /captions\.(srt|vtt).*source line \d+/);
      assert.match(browser.alerts[0], /Text to review:/);
      return;
    }
    await browser.call('convertSelectedFile');
    assert.equal(browser.elements.get('results').children.length, 3);
    const cues = browser.call(parse, c.source);
    for (const ext of ['srt', 'vtt']) {
      const actual = browser.call(ext === 'srt' ? 'cuesToSrt' : 'cuesToVtt', cues);
      assert.equal(actual, c.expected_browser[ext]);
    }
    const actual = JSON.parse(JSON.stringify(cues));
    assert.equal(actual.length, c.expected_cues.length);
    actual.forEach((cue, index) => {
      assert.deepEqual(cue.text, c.expected_cues[index].text);
      assert.ok(Math.abs(cue.start - c.expected_cues[index].start) < 1e-8);
      assert.ok(Math.abs(cue.end - c.expected_cues[index].end) < 1e-8);
    });
    assert.equal(browser.call('prepareCaptionContent', c.source, c.format).replace(/\r\n|\r/g, '\n'), c.repaired_source.replace(/\r\n|\r/g, '\n'));
    if (c.name.startsWith('clean_')) assert.equal(browser.call('prepareCaptionContent', c.source, c.format), c.source);
    // Starting another file removes stale downloads before any validation failure.
    browser.call('handleFiles', [{name: 'other.srt', text: async () => ''}]);
    assert.equal(browser.elements.get('results').children.length, 0);
  });
}
