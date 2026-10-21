/*
 * Synthetic ScholarChain review-page scenario for the persistent cua_repl runtime.
 * Run these helpers through mcp__cua_repl.js after reading its documentation.
 * No browser package installation, DOM injection, source HTML execution, network
 * navigation, or real human annotations are used. Generated label clicks are tests.
 *
 * Native AX indices are ephemeral: every helper reacquires a full tree, matches an
 * observed accessible control, then acts. Do not use global new-tab/typeText
 * shortcuts: they can target another tab when the user uses Edge concurrently.
 */
var reviewBrowser = await cua.getApp('Microsoft Edge');
var reviewPrefix = 'file:///Users/danny/Documents/UIC/CS441/ScholarChain/modules/entity-resolution/src/main/resources/review/index.html';
async function reviewState() {
  return await reviewBrowser.getAXState({ emit: false, disableDiffing: true });
}
function observedIndex(state, pattern) {
  const matches = state.split('\n').filter(line => pattern.test(line));
  if (matches.length !== 1) throw Error('Expected one observed control: ' + pattern);
  const match = matches[0].match(/^\s*(\d+) /);
  if (!match) throw Error('Missing AX index');
  return Number(match[1]);
}
async function assertReviewTab() {
  const state = await reviewState();
  if (!state.includes('URL: ' + reviewPrefix)) throw Error('Local review tab is not active; stop and select its observed tab.');
  return state;
}
async function clickReview(pattern) {
  const state = await assertReviewTab();
  await reviewBrowser.click(observedIndex(state, pattern));
  return await reviewState();
}
async function setReview(pattern, value) {
  const state = await assertReviewTab();
  await reviewBrowser.setValue(observedIndex(state, pattern), value);
  return await reviewState();
}
async function chooseReviewFile(buttonPattern, path) {
  await clickReview(buttonPattern);
  let state = await reviewState();
  if (!state.includes('Description: open')) throw Error('Expected native file chooser');
  await reviewBrowser.pressKey('super+shift+g');
  state = await reviewState();
  await reviewBrowser.setValue(observedIndex(state, /text field .*PathTextField/), path);
  await reviewBrowser.pressKey('Return');
  state = await reviewState();
  await reviewBrowser.click(observedIndex(state, /button Open, ID: OKButton/));
  return await reviewState();
}
function requireVisible(state, text) {
  if (!state.includes(text)) throw Error('Expected visible UI result: ' + text);
}
/* Scenario, executed stepwise with fresh observations between each action:
1. Select existing "ScholarChain blind review" tab by its observed AX index.
2. chooseReviewFile(/button Load review queue:/, TARGET + '/queue.json');
   requireVisible(state, '0 of 6 initial tasks answered; 6 remaining.');
   requireVisible(state, "<img src=x onerror=alert('SOURCE_HTML_MUST_NOT_EXECUTE')>");
   requireVisible(state, 'No answer selected.'); no alert or fetched image appears.
3. clickReview(/button Same$/); require reviewer-ID validation error.
4. setReview(/text field .*Your reviewer ID/, 'SYNTHETIC-CUA-TEST-ONLY');
   setReview(/text entry area .*Optional evidence note/, 'Automated browser test only; source HTML is displayed as text.');
   clickReview(/button Same$/); require same revision 1; progress 1/6.
5. clickReview(/button Next \/ skip$/); require blank task 2.
   clickReview(/button Different$/); require different revision 1; progress 2/6.
6. Next; Uncertain; require progress 3/6 and uncertain revision 1.
   Undo; require no answer and progress 2/6.
   Uncertain; require uncertain revision 3 and progress 3/6.
7. Next; require Researcher task and author ordinal/name/ORCID-missing context.
8. Save checkpoint; require download acknowledgement. Verify actual new downloaded
   JSON, then preserve/copy it into synthetic target directory for explicit resume.
9. chooseReviewFile(/button Resume checkpoint:/, TARGET + '/other-queue-checkpoint.json');
   require 'Checkpoint belongs to a different queue.' and unchanged progress 3/6.
10. Click observed browser Refresh. Require blank queue and disabled Save/Resume.
11. Load original queue then downloaded-synthetic-checkpoint.json.
    Require 'Checkpoint resumed; original file preserved.', progress 3/6,
    task 1 same revision 1, task 2 different revision 1, task 3 uncertain revision 3.

TARGET=/Users/danny/Documents/UIC/CS441/ScholarChain/target/phase5c-browser-synthetic-1
These labels are automated test fixtures, never valid human identity evidence.
*/
