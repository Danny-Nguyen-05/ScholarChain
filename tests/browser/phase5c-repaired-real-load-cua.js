/* Run stepwise in mcp__cua_repl.js after reading its documentation.
 * This is load-only: no reviewer entry, labels, notes, navigation or checkpoint actions.
 * Every index below must be resolved from a freshly observed native AX tree.
 */
var edgeRealLoad = await cua.getApp('Microsoft Edge');
async function stateRealLoad() {
  return await edgeRealLoad.getAXState({ emit: false, disableDiffing: true });
}
function axIndexRealLoad(state, regex) {
  const lines = state.split('\n').filter(line => regex.test(line));
  if (lines.length !== 1) throw Error('Expected one observed control: ' + regex);
  return Number(lines[0].match(/^\s*(\d+) /)[1]);
}
/* Sequence executed with fresh observations after each action:
1. Click observed button New Tab. Verify edge://newtab and its address field.
2. Set only that observed address field to:
   file:///Users/danny/Documents/UIC/CS441/ScholarChain/target/phase5c-repair-review-tool/index.html
   Press Return; verify exact local URL and blank "Load a queue to begin." state.
3. Click observed button "Load review queue: No file chosen".
4. In the confirmed native open chooser, press super+shift+g.
   Set observed PathTextField to:
   /Users/danny/Documents/UIC/CS441/ScholarChain/docs/agent-runs/phase-05/evidence/5c-repair/review-artifacts/queue.json
   Press Return. Verify queue.json selected in review-artifacts, then click observed enabled Open.
5. Require actual AX text:
   "0 of 240 initial tasks answered; 240 remaining."
   "Work task 1 of 240"
   "No answer selected."
   Reviewer ID field must remain blank.
6. Stop. Do not click label, save, resume or note controls.

Observed receipt: phase5c-repaired-real-load-observed.json.
*/
