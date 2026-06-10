import { e as I, d as M } from "./monaco-4.7.0.js";
var N = Object.defineProperty, R = Object.getOwnPropertyDescriptor, E = Object.getOwnPropertyNames, K = Object.prototype.hasOwnProperty, H = (e, t, r, a) => {
  if (t && typeof t == "object" || typeof t == "function")
    for (let n of E(t))
      !K.call(e, n) && n !== r && N(e, n, { get: () => t[n], enumerable: !(a = R(t, n)) || a.enumerable });
  return e;
}, W = (e, t, r) => (H(e, t, "default"), r), o = {};
W(o, M);
function j(e, t) {
  const r = globalThis.MonacoEnvironment;
  if (r?.createTrustedTypesPolicy)
    try {
      return r.createTrustedTypesPolicy(e, t);
    } catch (a) {
      console.error(a);
      return;
    }
  try {
    return globalThis.trustedTypes?.createPolicy(e, t);
  } catch (a) {
    console.error(a);
    return;
  }
}
var D;
typeof self == "object" && self.constructor && self.constructor.name === "DedicatedWorkerGlobalScope" && globalThis.workerttPolicy !== void 0 ? D = globalThis.workerttPolicy : D = j("defaultWorkerFactory", {
  createScriptURL: (e) => e
});
function V(e) {
  const t = e.label, r = globalThis.MonacoEnvironment;
  if (r) {
    if (typeof r.getWorker == "function")
      return r.getWorker("workerMain.js", t);
    if (typeof r.getWorkerUrl == "function") {
      const a = r.getWorkerUrl("workerMain.js", t);
      return new Worker(
        D ? D.createScriptURL(a) : a,
        { name: t, type: "module" }
      );
    }
  }
  throw new Error(
    "You must define a function MonacoEnvironment.getWorkerUrl or MonacoEnvironment.getWorker"
  );
}
function U(e) {
  const t = Promise.resolve(
    V({
      label: e.label ?? "monaco-editor-worker"
    })
  ).then((r) => (r.postMessage("ignore"), r.postMessage(e.createData), r));
  return o.editor.createWebWorker({
    worker: t,
    host: e.host,
    keepIdleModels: e.keepIdleModels
  });
}
var B = class {
  constructor(e, t) {
    this._modeId = e, this._defaults = t, this._worker = null, this._client = null, this._configChangeListener = this._defaults.onDidChange(() => this._stopWorker()), this._updateExtraLibsToken = 0, this._extraLibsChangeListener = this._defaults.onDidExtraLibsChange(
      () => this._updateExtraLibs()
    );
  }
  dispose() {
    this._configChangeListener.dispose(), this._extraLibsChangeListener.dispose(), this._stopWorker();
  }
  _stopWorker() {
    this._worker && (this._worker.dispose(), this._worker = null), this._client = null;
  }
  async _updateExtraLibs() {
    if (!this._worker)
      return;
    const e = ++this._updateExtraLibsToken, t = await this._worker.getProxy();
    this._updateExtraLibsToken === e && t.updateExtraLibs(this._defaults.getExtraLibs());
  }
  _getClient() {
    return this._client || (this._client = (async () => (this._worker = U({
      label: this._modeId,
      keepIdleModels: !0,
      // passed in to the create() method
      createData: {
        compilerOptions: this._defaults.getCompilerOptions(),
        extraLibs: this._defaults.getExtraLibs(),
        customWorkerPath: this._defaults.workerOptions.customWorkerPath,
        inlayHintsOptions: this._defaults.inlayHintsOptions
      }
    }), this._defaults.getEagerModelSync() ? await this._worker.withSyncedResources(
      o.editor.getModels().filter((e) => e.getLanguageId() === this._modeId).map((e) => e.uri)
    ) : await this._worker.getProxy()))()), this._client;
  }
  async getLanguageServiceWorker(...e) {
    const t = await this._getClient();
    return this._worker && await this._worker.withSyncedResources(e), t;
  }
}, i = {};
i["lib.d.ts"] = !0;
i["lib.decorators.d.ts"] = !0;
i["lib.decorators.legacy.d.ts"] = !0;
i["lib.dom.asynciterable.d.ts"] = !0;
i["lib.dom.d.ts"] = !0;
i["lib.dom.iterable.d.ts"] = !0;
i["lib.es2015.collection.d.ts"] = !0;
i["lib.es2015.core.d.ts"] = !0;
i["lib.es2015.d.ts"] = !0;
i["lib.es2015.generator.d.ts"] = !0;
i["lib.es2015.iterable.d.ts"] = !0;
i["lib.es2015.promise.d.ts"] = !0;
i["lib.es2015.proxy.d.ts"] = !0;
i["lib.es2015.reflect.d.ts"] = !0;
i["lib.es2015.symbol.d.ts"] = !0;
i["lib.es2015.symbol.wellknown.d.ts"] = !0;
i["lib.es2016.array.include.d.ts"] = !0;
i["lib.es2016.d.ts"] = !0;
i["lib.es2016.full.d.ts"] = !0;
i["lib.es2016.intl.d.ts"] = !0;
i["lib.es2017.d.ts"] = !0;
i["lib.es2017.date.d.ts"] = !0;
i["lib.es2017.full.d.ts"] = !0;
i["lib.es2017.intl.d.ts"] = !0;
i["lib.es2017.object.d.ts"] = !0;
i["lib.es2017.sharedmemory.d.ts"] = !0;
i["lib.es2017.string.d.ts"] = !0;
i["lib.es2017.typedarrays.d.ts"] = !0;
i["lib.es2018.asyncgenerator.d.ts"] = !0;
i["lib.es2018.asynciterable.d.ts"] = !0;
i["lib.es2018.d.ts"] = !0;
i["lib.es2018.full.d.ts"] = !0;
i["lib.es2018.intl.d.ts"] = !0;
i["lib.es2018.promise.d.ts"] = !0;
i["lib.es2018.regexp.d.ts"] = !0;
i["lib.es2019.array.d.ts"] = !0;
i["lib.es2019.d.ts"] = !0;
i["lib.es2019.full.d.ts"] = !0;
i["lib.es2019.intl.d.ts"] = !0;
i["lib.es2019.object.d.ts"] = !0;
i["lib.es2019.string.d.ts"] = !0;
i["lib.es2019.symbol.d.ts"] = !0;
i["lib.es2020.bigint.d.ts"] = !0;
i["lib.es2020.d.ts"] = !0;
i["lib.es2020.date.d.ts"] = !0;
i["lib.es2020.full.d.ts"] = !0;
i["lib.es2020.intl.d.ts"] = !0;
i["lib.es2020.number.d.ts"] = !0;
i["lib.es2020.promise.d.ts"] = !0;
i["lib.es2020.sharedmemory.d.ts"] = !0;
i["lib.es2020.string.d.ts"] = !0;
i["lib.es2020.symbol.wellknown.d.ts"] = !0;
i["lib.es2021.d.ts"] = !0;
i["lib.es2021.full.d.ts"] = !0;
i["lib.es2021.intl.d.ts"] = !0;
i["lib.es2021.promise.d.ts"] = !0;
i["lib.es2021.string.d.ts"] = !0;
i["lib.es2021.weakref.d.ts"] = !0;
i["lib.es2022.array.d.ts"] = !0;
i["lib.es2022.d.ts"] = !0;
i["lib.es2022.error.d.ts"] = !0;
i["lib.es2022.full.d.ts"] = !0;
i["lib.es2022.intl.d.ts"] = !0;
i["lib.es2022.object.d.ts"] = !0;
i["lib.es2022.regexp.d.ts"] = !0;
i["lib.es2022.sharedmemory.d.ts"] = !0;
i["lib.es2022.string.d.ts"] = !0;
i["lib.es2023.array.d.ts"] = !0;
i["lib.es2023.collection.d.ts"] = !0;
i["lib.es2023.d.ts"] = !0;
i["lib.es2023.full.d.ts"] = !0;
i["lib.es5.d.ts"] = !0;
i["lib.es6.d.ts"] = !0;
i["lib.esnext.collection.d.ts"] = !0;
i["lib.esnext.d.ts"] = !0;
i["lib.esnext.decorators.d.ts"] = !0;
i["lib.esnext.disposable.d.ts"] = !0;
i["lib.esnext.full.d.ts"] = !0;
i["lib.esnext.intl.d.ts"] = !0;
i["lib.esnext.object.d.ts"] = !0;
i["lib.esnext.promise.d.ts"] = !0;
i["lib.scripthost.d.ts"] = !0;
i["lib.webworker.asynciterable.d.ts"] = !0;
i["lib.webworker.d.ts"] = !0;
i["lib.webworker.importscripts.d.ts"] = !0;
i["lib.webworker.iterable.d.ts"] = !0;
function T(e, t, r = 0) {
  if (typeof e == "string")
    return e;
  if (e === void 0)
    return "";
  let a = "";
  if (r) {
    a += t;
    for (let n = 0; n < r; n++)
      a += "  ";
  }
  if (a += e.messageText, r++, e.next)
    for (const n of e.next)
      a += T(n, t, r);
  return a;
}
function w(e) {
  return e ? e.map((t) => t.text).join("") : "";
}
var y = class {
  constructor(e) {
    this._worker = e;
  }
  // protected _positionToOffset(model: editor.ITextModel, position: monaco.IPosition): number {
  // 	return model.getOffsetAt(position);
  // }
  // protected _offsetToPosition(model: editor.ITextModel, offset: number): monaco.IPosition {
  // 	return model.getPositionAt(offset);
  // }
  _textSpanToRange(e, t) {
    let r = e.getPositionAt(t.start), a = e.getPositionAt(t.start + t.length), { lineNumber: n, column: l } = r, { lineNumber: u, column: s } = a;
    return { startLineNumber: n, startColumn: l, endLineNumber: u, endColumn: s };
  }
}, $ = class {
  constructor(e) {
    this._worker = e, this._libFiles = {}, this._hasFetchedLibFiles = !1, this._fetchLibFilesPromise = null;
  }
  isLibFile(e) {
    return e && e.path.indexOf("/lib.") === 0 ? !!i[e.path.slice(1)] : !1;
  }
  getOrCreateModel(e) {
    const t = o.Uri.parse(e), r = o.editor.getModel(t);
    if (r)
      return r;
    if (this.isLibFile(t) && this._hasFetchedLibFiles)
      return o.editor.createModel(this._libFiles[t.path.slice(1)], "typescript", t);
    const a = I.getExtraLibs()[e];
    return a ? o.editor.createModel(a.content, "typescript", t) : null;
  }
  _containsLibFile(e) {
    for (let t of e)
      if (this.isLibFile(t))
        return !0;
    return !1;
  }
  async fetchLibFilesIfNecessary(e) {
    this._containsLibFile(e) && await this._fetchLibFiles();
  }
  _fetchLibFiles() {
    return this._fetchLibFilesPromise || (this._fetchLibFilesPromise = this._worker().then((e) => e.getLibFiles()).then((e) => {
      this._hasFetchedLibFiles = !0, this._libFiles = e;
    })), this._fetchLibFilesPromise;
  }
}, z = class extends y {
  constructor(e, t, r, a) {
    super(a), this._libFiles = e, this._defaults = t, this._selector = r, this._disposables = [], this._listener = /* @__PURE__ */ Object.create(null);
    const n = (s) => {
      if (s.getLanguageId() !== r)
        return;
      const c = () => {
        const { onlyVisible: h } = this._defaults.getDiagnosticsOptions();
        h ? s.isAttachedToEditor() && this._doValidate(s) : this._doValidate(s);
      };
      let g;
      const d = s.onDidChangeContent(() => {
        clearTimeout(g), g = window.setTimeout(c, 500);
      }), b = s.onDidChangeAttached(() => {
        const { onlyVisible: h } = this._defaults.getDiagnosticsOptions();
        h && (s.isAttachedToEditor() ? c() : o.editor.setModelMarkers(s, this._selector, []));
      });
      this._listener[s.uri.toString()] = {
        dispose() {
          d.dispose(), b.dispose(), clearTimeout(g);
        }
      }, c();
    }, l = (s) => {
      o.editor.setModelMarkers(s, this._selector, []);
      const c = s.uri.toString();
      this._listener[c] && (this._listener[c].dispose(), delete this._listener[c]);
    };
    this._disposables.push(
      o.editor.onDidCreateModel((s) => n(s))
    ), this._disposables.push(o.editor.onWillDisposeModel(l)), this._disposables.push(
      o.editor.onDidChangeModelLanguage((s) => {
        l(s.model), n(s.model);
      })
    ), this._disposables.push({
      dispose() {
        for (const s of o.editor.getModels())
          l(s);
      }
    });
    const u = () => {
      for (const s of o.editor.getModels())
        l(s), n(s);
    };
    this._disposables.push(this._defaults.onDidChange(u)), this._disposables.push(this._defaults.onDidExtraLibsChange(u)), o.editor.getModels().forEach((s) => n(s));
  }
  dispose() {
    this._disposables.forEach((e) => e && e.dispose()), this._disposables = [];
  }
  async _doValidate(e) {
    const t = await this._worker(e.uri);
    if (e.isDisposed())
      return;
    const r = [], { noSyntaxValidation: a, noSemanticValidation: n, noSuggestionDiagnostics: l } = this._defaults.getDiagnosticsOptions();
    a || r.push(t.getSyntacticDiagnostics(e.uri.toString())), n || r.push(t.getSemanticDiagnostics(e.uri.toString())), l || r.push(t.getSuggestionDiagnostics(e.uri.toString()));
    const u = await Promise.all(r);
    if (!u || e.isDisposed())
      return;
    const s = u.reduce((g, d) => d.concat(g), []).filter(
      (g) => (this._defaults.getDiagnosticsOptions().diagnosticCodesToIgnore || []).indexOf(g.code) === -1
    ), c = s.map((g) => g.relatedInformation || []).reduce((g, d) => d.concat(g), []).map(
      (g) => g.file ? o.Uri.parse(g.file.fileName) : null
    );
    await this._libFiles.fetchLibFilesIfNecessary(c), !e.isDisposed() && o.editor.setModelMarkers(
      e,
      this._selector,
      s.map((g) => this._convertDiagnostics(e, g))
    );
  }
  _convertDiagnostics(e, t) {
    const r = t.start || 0, a = t.length || 1, { lineNumber: n, column: l } = e.getPositionAt(r), { lineNumber: u, column: s } = e.getPositionAt(
      r + a
    ), c = [];
    return t.reportsUnnecessary && c.push(o.MarkerTag.Unnecessary), t.reportsDeprecated && c.push(o.MarkerTag.Deprecated), {
      severity: this._tsDiagnosticCategoryToMarkerSeverity(t.category),
      startLineNumber: n,
      startColumn: l,
      endLineNumber: u,
      endColumn: s,
      message: T(t.messageText, `
`),
      code: t.code.toString(),
      tags: c,
      relatedInformation: this._convertRelatedInformation(e, t.relatedInformation)
    };
  }
  _convertRelatedInformation(e, t) {
    if (!t)
      return [];
    const r = [];
    return t.forEach((a) => {
      let n = e;
      if (a.file && (n = this._libFiles.getOrCreateModel(a.file.fileName)), !n)
        return;
      const l = a.start || 0, u = a.length || 1, { lineNumber: s, column: c } = n.getPositionAt(l), { lineNumber: g, column: d } = n.getPositionAt(
        l + u
      );
      r.push({
        resource: n.uri,
        startLineNumber: s,
        startColumn: c,
        endLineNumber: g,
        endColumn: d,
        message: T(a.messageText, `
`)
      });
    }), r;
  }
  _tsDiagnosticCategoryToMarkerSeverity(e) {
    switch (e) {
      case 1:
        return o.MarkerSeverity.Error;
      case 3:
        return o.MarkerSeverity.Info;
      case 0:
        return o.MarkerSeverity.Warning;
      case 2:
        return o.MarkerSeverity.Hint;
    }
    return o.MarkerSeverity.Info;
  }
}, G = class C extends y {
  get triggerCharacters() {
    return ["."];
  }
  async provideCompletionItems(t, r, a, n) {
    const l = t.getWordUntilPosition(r), u = new o.Range(
      r.lineNumber,
      l.startColumn,
      r.lineNumber,
      l.endColumn
    ), s = t.uri, c = t.getOffsetAt(r), g = await this._worker(s);
    if (t.isDisposed())
      return;
    const d = await g.getCompletionsAtPosition(s.toString(), c);
    return !d || t.isDisposed() ? void 0 : {
      suggestions: d.entries.map((h) => {
        let _ = u;
        if (h.replacementSpan) {
          const S = t.getPositionAt(h.replacementSpan.start), x = t.getPositionAt(h.replacementSpan.start + h.replacementSpan.length);
          _ = new o.Range(S.lineNumber, S.column, x.lineNumber, x.column);
        }
        const v = [];
        return h.kindModifiers !== void 0 && h.kindModifiers.indexOf("deprecated") !== -1 && v.push(o.languages.CompletionItemTag.Deprecated), {
          uri: s,
          position: r,
          offset: c,
          range: _,
          label: h.name,
          insertText: h.name,
          sortText: h.sortText,
          kind: C.convertKind(h.kind),
          tags: v
        };
      })
    };
  }
  async resolveCompletionItem(t, r) {
    const a = t, n = a.uri, l = a.position, u = a.offset, c = await (await this._worker(n)).getCompletionEntryDetails(
      n.toString(),
      u,
      a.label
    );
    return c ? {
      uri: n,
      position: l,
      label: c.name,
      kind: C.convertKind(c.kind),
      detail: w(c.displayParts),
      documentation: {
        value: C.createDocumentationString(c)
      }
    } : a;
  }
  static convertKind(t) {
    switch (t) {
      case f.primitiveType:
      case f.keyword:
        return o.languages.CompletionItemKind.Keyword;
      case f.variable:
      case f.localVariable:
        return o.languages.CompletionItemKind.Variable;
      case f.memberVariable:
      case f.memberGetAccessor:
      case f.memberSetAccessor:
        return o.languages.CompletionItemKind.Field;
      case f.function:
      case f.memberFunction:
      case f.constructSignature:
      case f.callSignature:
      case f.indexSignature:
        return o.languages.CompletionItemKind.Function;
      case f.enum:
        return o.languages.CompletionItemKind.Enum;
      case f.module:
        return o.languages.CompletionItemKind.Module;
      case f.class:
        return o.languages.CompletionItemKind.Class;
      case f.interface:
        return o.languages.CompletionItemKind.Interface;
      case f.warning:
        return o.languages.CompletionItemKind.File;
    }
    return o.languages.CompletionItemKind.Property;
  }
  static createDocumentationString(t) {
    let r = w(t.documentation);
    if (t.tags)
      for (const a of t.tags)
        r += `

${P(a)}`;
    return r;
  }
};
function P(e) {
  let t = `*@${e.name}*`;
  if (e.name === "param" && e.text) {
    const [r, ...a] = e.text;
    t += `\`${r.text}\``, a.length > 0 && (t += ` — ${a.map((n) => n.text).join(" ")}`);
  } else Array.isArray(e.text) ? t += ` — ${e.text.map((r) => r.text).join(" ")}` : e.text && (t += ` — ${e.text}`);
  return t;
}
var J = class L extends y {
  constructor() {
    super(...arguments), this.signatureHelpTriggerCharacters = ["(", ","];
  }
  static _toSignatureHelpTriggerReason(t) {
    switch (t.triggerKind) {
      case o.languages.SignatureHelpTriggerKind.TriggerCharacter:
        return t.triggerCharacter ? t.isRetrigger ? { kind: "retrigger", triggerCharacter: t.triggerCharacter } : { kind: "characterTyped", triggerCharacter: t.triggerCharacter } : { kind: "invoked" };
      case o.languages.SignatureHelpTriggerKind.ContentChange:
        return t.isRetrigger ? { kind: "retrigger" } : { kind: "invoked" };
      case o.languages.SignatureHelpTriggerKind.Invoke:
      default:
        return { kind: "invoked" };
    }
  }
  async provideSignatureHelp(t, r, a, n) {
    const l = t.uri, u = t.getOffsetAt(r), s = await this._worker(l);
    if (t.isDisposed())
      return;
    const c = await s.getSignatureHelpItems(l.toString(), u, {
      triggerReason: L._toSignatureHelpTriggerReason(n)
    });
    if (!c || t.isDisposed())
      return;
    const g = {
      activeSignature: c.selectedItemIndex,
      activeParameter: c.argumentIndex,
      signatures: []
    };
    return c.items.forEach((d) => {
      const b = {
        label: "",
        parameters: []
      };
      b.documentation = {
        value: w(d.documentation)
      }, b.label += w(d.prefixDisplayParts), d.parameters.forEach((h, _, v) => {
        const S = w(h.displayParts), x = {
          label: S,
          documentation: {
            value: w(h.documentation)
          }
        };
        b.label += S, b.parameters.push(x), _ < v.length - 1 && (b.label += w(d.separatorDisplayParts));
      }), b.label += w(d.suffixDisplayParts), g.signatures.push(b);
    }), {
      value: g,
      dispose() {
      }
    };
  }
}, Q = class extends y {
  async provideHover(e, t, r) {
    const a = e.uri, n = e.getOffsetAt(t), l = await this._worker(a);
    if (e.isDisposed())
      return;
    const u = await l.getQuickInfoAtPosition(a.toString(), n);
    if (!u || e.isDisposed())
      return;
    const s = w(u.documentation), c = u.tags ? u.tags.map((d) => P(d)).join(`  

`) : "", g = w(u.displayParts);
    return {
      range: this._textSpanToRange(e, u.textSpan),
      contents: [
        {
          value: "```typescript\n" + g + "\n```\n"
        },
        {
          value: s + (c ? `

` + c : "")
        }
      ]
    };
  }
}, q = class extends y {
  async provideDocumentHighlights(e, t, r) {
    const a = e.uri, n = e.getOffsetAt(t), l = await this._worker(a);
    if (e.isDisposed())
      return;
    const u = await l.getDocumentHighlights(a.toString(), n, [
      a.toString()
    ]);
    if (!(!u || e.isDisposed()))
      return u.flatMap((s) => s.highlightSpans.map((c) => ({
        range: this._textSpanToRange(e, c.textSpan),
        kind: c.kind === "writtenReference" ? o.languages.DocumentHighlightKind.Write : o.languages.DocumentHighlightKind.Text
      })));
  }
}, Y = class extends y {
  constructor(e, t) {
    super(t), this._libFiles = e;
  }
  async provideDefinition(e, t, r) {
    const a = e.uri, n = e.getOffsetAt(t), l = await this._worker(a);
    if (e.isDisposed())
      return;
    const u = await l.getDefinitionAtPosition(a.toString(), n);
    if (!u || e.isDisposed() || (await this._libFiles.fetchLibFilesIfNecessary(
      u.map((c) => o.Uri.parse(c.fileName))
    ), e.isDisposed()))
      return;
    const s = [];
    for (let c of u) {
      const g = this._libFiles.getOrCreateModel(c.fileName);
      g && s.push({
        uri: g.uri,
        range: this._textSpanToRange(g, c.textSpan)
      });
    }
    return s;
  }
}, X = class extends y {
  constructor(e, t) {
    super(t), this._libFiles = e;
  }
  async provideReferences(e, t, r, a) {
    const n = e.uri, l = e.getOffsetAt(t), u = await this._worker(n);
    if (e.isDisposed())
      return;
    const s = await u.getReferencesAtPosition(n.toString(), l);
    if (!s || e.isDisposed() || (await this._libFiles.fetchLibFilesIfNecessary(
      s.map((g) => o.Uri.parse(g.fileName))
    ), e.isDisposed()))
      return;
    const c = [];
    for (let g of s) {
      const d = this._libFiles.getOrCreateModel(g.fileName);
      d && c.push({
        uri: d.uri,
        range: this._textSpanToRange(d, g.textSpan)
      });
    }
    return c;
  }
}, Z = class extends y {
  async provideDocumentSymbols(e, t) {
    const r = e.uri, a = await this._worker(r);
    if (e.isDisposed())
      return;
    const n = await a.getNavigationTree(r.toString());
    if (!n || e.isDisposed())
      return;
    const l = (s, c) => ({
      name: s.text,
      detail: "",
      kind: m[s.kind] || o.languages.SymbolKind.Variable,
      range: this._textSpanToRange(e, s.spans[0]),
      selectionRange: this._textSpanToRange(e, s.spans[0]),
      tags: [],
      children: s.childItems?.map((d) => l(d, s.text)),
      containerName: c
    });
    return n.childItems ? n.childItems.map((s) => l(s)) : [];
  }
}, p, f = (p = class {
}, p.unknown = "", p.keyword = "keyword", p.script = "script", p.module = "module", p.class = "class", p.interface = "interface", p.type = "type", p.enum = "enum", p.variable = "var", p.localVariable = "local var", p.function = "function", p.localFunction = "local function", p.memberFunction = "method", p.memberGetAccessor = "getter", p.memberSetAccessor = "setter", p.memberVariable = "property", p.constructorImplementation = "constructor", p.callSignature = "call", p.indexSignature = "index", p.constructSignature = "construct", p.parameter = "parameter", p.typeParameter = "type parameter", p.primitiveType = "primitive type", p.label = "label", p.alias = "alias", p.const = "const", p.let = "let", p.warning = "warning", p), m = /* @__PURE__ */ Object.create(null);
m[f.module] = o.languages.SymbolKind.Module;
m[f.class] = o.languages.SymbolKind.Class;
m[f.enum] = o.languages.SymbolKind.Enum;
m[f.interface] = o.languages.SymbolKind.Interface;
m[f.memberFunction] = o.languages.SymbolKind.Method;
m[f.memberVariable] = o.languages.SymbolKind.Property;
m[f.memberGetAccessor] = o.languages.SymbolKind.Property;
m[f.memberSetAccessor] = o.languages.SymbolKind.Property;
m[f.variable] = o.languages.SymbolKind.Variable;
m[f.const] = o.languages.SymbolKind.Variable;
m[f.localVariable] = o.languages.SymbolKind.Variable;
m[f.variable] = o.languages.SymbolKind.Variable;
m[f.function] = o.languages.SymbolKind.Function;
m[f.localFunction] = o.languages.SymbolKind.Function;
var k = class extends y {
  static _convertOptions(e) {
    return {
      ConvertTabsToSpaces: e.insertSpaces,
      TabSize: e.tabSize,
      IndentSize: e.tabSize,
      IndentStyle: 2,
      NewLineCharacter: `
`,
      InsertSpaceAfterCommaDelimiter: !0,
      InsertSpaceAfterSemicolonInForStatements: !0,
      InsertSpaceBeforeAndAfterBinaryOperators: !0,
      InsertSpaceAfterKeywordsInControlFlowStatements: !0,
      InsertSpaceAfterFunctionKeywordForAnonymousFunctions: !0,
      InsertSpaceAfterOpeningAndBeforeClosingNonemptyParenthesis: !1,
      InsertSpaceAfterOpeningAndBeforeClosingNonemptyBrackets: !1,
      InsertSpaceAfterOpeningAndBeforeClosingTemplateStringBraces: !1,
      PlaceOpenBraceOnNewLineForControlBlocks: !1,
      PlaceOpenBraceOnNewLineForFunctions: !1
    };
  }
  _convertTextChanges(e, t) {
    return {
      text: t.newText,
      range: this._textSpanToRange(e, t.span)
    };
  }
}, ee = class extends k {
  constructor() {
    super(...arguments), this.canFormatMultipleRanges = !1;
  }
  async provideDocumentRangeFormattingEdits(e, t, r, a) {
    const n = e.uri, l = e.getOffsetAt({
      lineNumber: t.startLineNumber,
      column: t.startColumn
    }), u = e.getOffsetAt({
      lineNumber: t.endLineNumber,
      column: t.endColumn
    }), s = await this._worker(n);
    if (e.isDisposed())
      return;
    const c = await s.getFormattingEditsForRange(
      n.toString(),
      l,
      u,
      k._convertOptions(r)
    );
    if (!(!c || e.isDisposed()))
      return c.map((g) => this._convertTextChanges(e, g));
  }
}, te = class extends k {
  get autoFormatTriggerCharacters() {
    return [";", "}", `
`];
  }
  async provideOnTypeFormattingEdits(e, t, r, a, n) {
    const l = e.uri, u = e.getOffsetAt(t), s = await this._worker(l);
    if (e.isDisposed())
      return;
    const c = await s.getFormattingEditsAfterKeystroke(
      l.toString(),
      u,
      r,
      k._convertOptions(a)
    );
    if (!(!c || e.isDisposed()))
      return c.map((g) => this._convertTextChanges(e, g));
  }
}, re = class extends k {
  async provideCodeActions(e, t, r, a) {
    const n = e.uri, l = e.getOffsetAt({
      lineNumber: t.startLineNumber,
      column: t.startColumn
    }), u = e.getOffsetAt({
      lineNumber: t.endLineNumber,
      column: t.endColumn
    }), s = k._convertOptions(e.getOptions()), c = r.markers.filter((h) => h.code).map((h) => h.code).map(Number), g = await this._worker(n);
    if (e.isDisposed())
      return;
    const d = await g.getCodeFixesAtPosition(
      n.toString(),
      l,
      u,
      c,
      s
    );
    return !d || e.isDisposed() ? { actions: [], dispose: () => {
    } } : {
      actions: d.filter((h) => h.changes.filter((_) => _.isNewFile).length === 0).map((h) => this._tsCodeFixActionToMonacoCodeAction(e, r, h)),
      dispose: () => {
      }
    };
  }
  _tsCodeFixActionToMonacoCodeAction(e, t, r) {
    const a = [];
    for (const l of r.changes)
      for (const u of l.textChanges)
        a.push({
          resource: e.uri,
          versionId: void 0,
          textEdit: {
            range: this._textSpanToRange(e, u.span),
            text: u.newText
          }
        });
    return {
      title: r.description,
      edit: { edits: a },
      diagnostics: t.markers,
      kind: "quickfix"
    };
  }
}, se = class extends y {
  constructor(e, t) {
    super(t), this._libFiles = e;
  }
  async provideRenameEdits(e, t, r, a) {
    const n = e.uri, l = n.toString(), u = e.getOffsetAt(t), s = await this._worker(n);
    if (e.isDisposed())
      return;
    const c = await s.getRenameInfo(l, u, {
      allowRenameOfImportPath: !1
    });
    if (c.canRename === !1)
      return {
        edits: [],
        rejectReason: c.localizedErrorMessage
      };
    if (c.fileToRename !== void 0)
      throw new Error("Renaming files is not supported.");
    const g = await s.findRenameLocations(
      l,
      u,
      /*strings*/
      !1,
      /*comments*/
      !1,
      /*prefixAndSuffix*/
      !1
    );
    if (!g || e.isDisposed())
      return;
    const d = [];
    for (const b of g) {
      const h = this._libFiles.getOrCreateModel(b.fileName);
      if (h)
        d.push({
          resource: h.uri,
          versionId: void 0,
          textEdit: {
            range: this._textSpanToRange(h, b.textSpan),
            text: r
          }
        });
      else
        throw new Error(`Unknown file ${b.fileName}.`);
    }
    return { edits: d };
  }
}, ie = class extends y {
  async provideInlayHints(e, t, r) {
    const a = e.uri, n = a.toString(), l = e.getOffsetAt({
      lineNumber: t.startLineNumber,
      column: t.startColumn
    }), u = e.getOffsetAt({
      lineNumber: t.endLineNumber,
      column: t.endColumn
    }), s = await this._worker(a);
    return e.isDisposed() ? null : { hints: (await s.provideInlayHints(n, l, u)).map((d) => ({
      ...d,
      label: d.text,
      position: e.getPositionAt(d.position),
      kind: this._convertHintKind(d.kind)
    })), dispose: () => {
    } };
  }
  _convertHintKind(e) {
    switch (e) {
      case "Parameter":
        return o.languages.InlayHintKind.Parameter;
      case "Type":
        return o.languages.InlayHintKind.Type;
      default:
        return o.languages.InlayHintKind.Type;
    }
  }
}, A, F;
function ae(e) {
  F = O(e, "typescript");
}
function ce(e) {
  A = O(e, "javascript");
}
function le() {
  return new Promise((e, t) => {
    if (!A)
      return t("JavaScript not registered!");
    e(A);
  });
}
function ue() {
  return new Promise((e, t) => {
    if (!F)
      return t("TypeScript not registered!");
    e(F);
  });
}
function O(e, t) {
  const r = [], a = new B(t, e), n = (...s) => a.getLanguageServiceWorker(...s), l = new $(n);
  function u() {
    const { modeConfiguration: s } = e;
    ne(r), s.completionItems && r.push(
      o.languages.registerCompletionItemProvider(
        t,
        new G(n)
      )
    ), s.signatureHelp && r.push(
      o.languages.registerSignatureHelpProvider(
        t,
        new J(n)
      )
    ), s.hovers && r.push(
      o.languages.registerHoverProvider(t, new Q(n))
    ), s.documentHighlights && r.push(
      o.languages.registerDocumentHighlightProvider(
        t,
        new q(n)
      )
    ), s.definitions && r.push(
      o.languages.registerDefinitionProvider(
        t,
        new Y(l, n)
      )
    ), s.references && r.push(
      o.languages.registerReferenceProvider(
        t,
        new X(l, n)
      )
    ), s.documentSymbols && r.push(
      o.languages.registerDocumentSymbolProvider(
        t,
        new Z(n)
      )
    ), s.rename && r.push(
      o.languages.registerRenameProvider(
        t,
        new se(l, n)
      )
    ), s.documentRangeFormattingEdits && r.push(
      o.languages.registerDocumentRangeFormattingEditProvider(
        t,
        new ee(n)
      )
    ), s.onTypeFormattingEdits && r.push(
      o.languages.registerOnTypeFormattingEditProvider(
        t,
        new te(n)
      )
    ), s.codeActions && r.push(
      o.languages.registerCodeActionProvider(t, new re(n))
    ), s.inlayHints && r.push(
      o.languages.registerInlayHintsProvider(t, new ie(n))
    ), s.diagnostics && r.push(new z(l, e, t, n));
  }
  return u(), n;
}
function ne(e) {
  for (; e.length; )
    e.pop().dispose();
}
export {
  y as Adapter,
  re as CodeActionAdaptor,
  Y as DefinitionAdapter,
  z as DiagnosticsAdapter,
  q as DocumentHighlightAdapter,
  ee as FormatAdapter,
  k as FormatHelper,
  te as FormatOnTypeAdapter,
  ie as InlayHintsAdapter,
  f as Kind,
  $ as LibFiles,
  Z as OutlineAdapter,
  Q as QuickInfoAdapter,
  X as ReferenceAdapter,
  se as RenameAdapter,
  J as SignatureHelpAdapter,
  G as SuggestAdapter,
  B as WorkerManager,
  T as flattenDiagnosticMessageText,
  le as getJavaScriptWorker,
  ue as getTypeScriptWorker,
  ce as setupJavaScript,
  ae as setupTypeScript
};
