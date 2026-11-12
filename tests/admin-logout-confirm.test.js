import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

const script = readFileSync(new URL("../static/js/admin-logout-confirm.js", import.meta.url), "utf8");

function submitLogout(answers, formId = "logout-form") {
  let submitHandler;
  const prompts = [];
  const document = {
    addEventListener(type, handler) {
      assert.equal(type, "submit");
      submitHandler = handler;
    },
  };
  const window = {
    confirm(message) {
      prompts.push(message);
      return answers.shift();
    },
  };
  vm.runInNewContext(script, { document, window });

  const event = {
    target: { matches: (selector) => selector === `#${formId}` },
    defaultPrevented: false,
    preventDefault() { this.defaultPrevented = true; },
  };
  submitHandler(event);
  return { event, prompts };
}

test("logout submits only after both confirmations", () => {
  const { event, prompts } = submitLogout([true, true]);

  assert.equal(prompts.length, 2);
  assert.equal(event.defaultPrevented, false);
});

test("canceling either confirmation prevents logout", () => {
  for (const [answers, expectedPrompts] of [[[false], 1], [[true, false], 2]]) {
    const { event, prompts } = submitLogout(answers);
    assert.equal(event.defaultPrevented, true);
    assert.equal(prompts.length, expectedPrompts);
  }
});

test("other forms are not intercepted", () => {
  const { event, prompts } = submitLogout([], "login-form");

  assert.equal(event.defaultPrevented, false);
  assert.equal(prompts.length, 0);
});
