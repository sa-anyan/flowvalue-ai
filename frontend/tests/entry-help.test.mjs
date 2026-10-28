import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8");

test("Entry help disclosure supports pointer hover, click, keyboard and touch natively", () => {
  const help = read("../src/components/dashboard/entry-help.tsx");
  const css = read("../src/app/globals.css");
  assert.match(help, /<details className="entry-help">/);
  assert.match(help, /<summary aria-label=/);
  assert.match(help, /<CircleHelp/);
  assert.match(help, /entry-help-content/);
  assert.match(css, /\.entry-help:hover > \.entry-help-content/);
  assert.match(css, /\.entry-help\[open\] > \.entry-help-content/);
  assert.match(css, /\.entry-help > summary:focus-visible/);
});

test("Entry descriptive guidance is hidden behind help icons without hiding status and errors", () => {
  const entry = read("../src/components/dashboard/balance-import.tsx");
  const samples = read("../src/components/dashboard/import-sample-guide.tsx");
  assert.match(entry, /<EntryHelp label=\{\`Import requirements for/);
  assert.match(entry, /\{method\.help\}/);
  assert.match(entry, /<EntryHelp label="AI review and data sharing">/);
  assert.match(entry, /<EntryHelp label="How imported evidence is handled">/);
  assert.match(entry, /<EntryHelp label="Meaning of verified">/);
  assert.match(entry, /<EntryHelp label="Meaning of simulation validation">/);
  assert.doesNotMatch(entry, /className="upload-message" id="balance-import-guidance"/);
  assert.match(entry, /role="status"/);
  assert.match(entry, /className="error-banner" role="alert"/);
  assert.match(entry, /Issues &amp; missing information/);
  assert.match(samples, /<EntryHelp label=\{\`About the/);
  assert.match(samples, /\{sample\.notes\}/);
  assert.match(samples, /<EntryHelp label="How FlowValue uses sample files">/);
  assert.match(samples, /<EntryHelp label="Why there is no sample">/);
  assert.match(samples, /<EntryHelp label="Is a sample download required\?">/);
  assert.match(samples, /Preview sample/);
  assert.match(samples, /Download sample/);
  assert.match(samples, /Lock in selected source/);
});
