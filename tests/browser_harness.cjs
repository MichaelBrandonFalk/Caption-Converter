const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

class Element {
  constructor() {
    this.children = [];
    this.listeners = {};
    this.checked = true;
    this.textContent = '';
    this.classList = { add() {}, remove() {} };
  }
  set innerHTML(value) { this.html = value; this.children = []; }
  get innerHTML() { return this.html || ''; }
  appendChild(child) { this.children.push(child); }
  addEventListener(type, handler) { this.listeners[type] = handler; }
}

function loadBrowser(sourcePath = path.join(__dirname, '../site/app.js')) {
  const elements = new Map();
  const alerts = [];
  const context = vm.createContext({
    document: {
      getElementById(id) {
        if (!elements.has(id)) elements.set(id, new Element());
        return elements.get(id);
      },
      createElement: () => new Element(),
    },
    window: { alert: (message) => alerts.push(message) },
    console: { error() {} },
    Blob, URL,
  });
  vm.runInContext(fs.readFileSync(sourcePath, 'utf8'), context, { filename: sourcePath });
  const call = (name, ...args) => {
    context.testArgs = args;
    return vm.runInContext(`${name}(...testArgs)`, context);
  };
  return { context, elements, alerts, call };
}
module.exports = { loadBrowser };
