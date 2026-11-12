import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

const script = readFileSync(new URL("../static/js/logout-confirm.js", import.meta.url), "utf8");

function submitLogout(answers, logout = true) {
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
    target: { matches: (selector) => logout && selector === "[data-logout]" },
    defaultPrevented: false,
    preventDefault() { this.defaultPrevented = true; },
  };
  submitHandler(event);
  return { event, prompts };
}

test("account logout submits only after both confirmations", () => {
  const { event, prompts } = submitLogout([true, true]);

  assert.equal(prompts.length, 2);
  assert.equal(event.defaultPrevented, false);
});

test("canceling either account logout confirmation prevents it", () => {
  for (const [answers, expectedPrompts] of [[[false], 1], [[true, false], 2]]) {
    const { event, prompts } = submitLogout(answers);
    assert.equal(event.defaultPrevented, true);
    assert.equal(prompts.length, expectedPrompts);
  }
});

test("forms without the logout marker are left alone", () => {
  const { event, prompts } = submitLogout([], false);

  assert.equal(event.defaultPrevented, false);
  assert.equal(prompts.length, 0);
});
