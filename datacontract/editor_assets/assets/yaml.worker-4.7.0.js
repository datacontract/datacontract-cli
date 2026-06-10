class kg {
  constructor() {
    this.listeners = [], this.unexpectedErrorHandler = function(t) {
      setTimeout(() => {
        throw t.stack ? Xr.isErrorNoTelemetry(t) ? new Xr(t.message + `

` + t.stack) : new Error(t.message + `

` + t.stack) : t;
      }, 0);
    };
  }
  emit(t) {
    this.listeners.forEach((n) => {
      n(t);
    });
  }
  onUnexpectedError(t) {
    this.unexpectedErrorHandler(t), this.emit(t);
  }
  // For external errors, we don't want the listeners to be called
  onUnexpectedExternalError(t) {
    this.unexpectedErrorHandler(t);
  }
}
const Cg = new kg();
function Ni(e) {
  Fg(e) || Cg.onUnexpectedError(e);
}
function xo(e) {
  if (e instanceof Error) {
    const { name: t, message: n, cause: r } = e, s = e.stacktrace || e.stack;
    return {
      $isError: !0,
      name: t,
      message: n,
      stack: s,
      noTelemetry: Xr.isErrorNoTelemetry(e),
      cause: r ? xo(r) : void 0,
      code: e.code
    };
  }
  return e;
}
const No = "Canceled";
function Fg(e) {
  return e instanceof t1 ? !0 : e instanceof Error && e.name === No && e.message === No;
}
class t1 extends Error {
  constructor() {
    super(No), this.name = this.message;
  }
}
class Xr extends Error {
  constructor(t) {
    super(t), this.name = "CodeExpectedError";
  }
  static fromError(t) {
    if (t instanceof Xr)
      return t;
    const n = new Xr();
    return n.message = t.message, n.stack = t.stack, n;
  }
  static isErrorNoTelemetry(t) {
    return t.name === "CodeExpectedError";
  }
}
class Ge extends Error {
  constructor(t) {
    super(t || "An unexpected bug occurred."), Object.setPrototypeOf(this, Ge.prototype);
  }
}
function _g(e, t = "Unreachable") {
  throw new Error(t);
}
function Tg(e, t = "unexpected state") {
  if (!e)
    throw typeof t == "string" ? new Ge(`Assertion Failed: ${t}`) : t;
}
function Wi(e) {
  if (!e()) {
    debugger;
    e(), Ni(new Ge("Assertion Failed"));
  }
}
function n1(e, t) {
  let n = 0;
  for (; n < e.length - 1; ) {
    const r = e[n], s = e[n + 1];
    if (!t(r, s))
      return !1;
    n++;
  }
  return !0;
}
function Mg(e) {
  return typeof e == "string";
}
function Og(e) {
  return !!e && typeof e[Symbol.iterator] == "function";
}
var Hi;
(function(e) {
  function t(p) {
    return !!p && typeof p == "object" && typeof p[Symbol.iterator] == "function";
  }
  e.is = t;
  const n = Object.freeze([]);
  function r() {
    return n;
  }
  e.empty = r;
  function* s(p) {
    yield p;
  }
  e.single = s;
  function i(p) {
    return t(p) ? p : s(p);
  }
  e.wrap = i;
  function a(p) {
    return p || n;
  }
  e.from = a;
  function* o(p) {
    for (let E = p.length - 1; E >= 0; E--)
      yield p[E];
  }
  e.reverse = o;
  function l(p) {
    return !p || p[Symbol.iterator]().next().done === !0;
  }
  e.isEmpty = l;
  function u(p) {
    return p[Symbol.iterator]().next().value;
  }
  e.first = u;
  function f(p, E) {
    let w = 0;
    for (const L of p)
      if (E(L, w++))
        return !0;
    return !1;
  }
  e.some = f;
  function c(p, E) {
    let w = 0;
    for (const L of p)
      if (!E(L, w++))
        return !1;
    return !0;
  }
  e.every = c;
  function d(p, E) {
    for (const w of p)
      if (E(w))
        return w;
  }
  e.find = d;
  function* v(p, E) {
    for (const w of p)
      E(w) && (yield w);
  }
  e.filter = v;
  function* D(p, E) {
    let w = 0;
    for (const L of p)
      yield E(L, w++);
  }
  e.map = D;
  function* S(p, E) {
    let w = 0;
    for (const L of p)
      yield* E(L, w++);
  }
  e.flatMap = S;
  function* x(...p) {
    for (const E of p)
      Og(E) ? yield* E : yield E;
  }
  e.concat = x;
  function N(p, E, w) {
    let L = w;
    for (const C of p)
      L = E(L, C);
    return L;
  }
  e.reduce = N;
  function k(p) {
    let E = 0;
    for (const w of p)
      E++;
    return E;
  }
  e.length = k;
  function* y(p, E, w = p.length) {
    for (E < -p.length && (E = 0), E < 0 && (E += p.length), w < 0 ? w += p.length : w > p.length && (w = p.length); E < w; E++)
      yield p[E];
  }
  e.slice = y;
  function b(p, E = Number.POSITIVE_INFINITY) {
    const w = [];
    if (E === 0)
      return [w, p];
    const L = p[Symbol.iterator]();
    for (let C = 0; C < E; C++) {
      const A = L.next();
      if (A.done)
        return [w, e.empty()];
      w.push(A.value);
    }
    return [w, { [Symbol.iterator]() {
      return L;
    } }];
  }
  e.consume = b;
  async function h(p) {
    const E = [];
    for await (const w of p)
      E.push(w);
    return E;
  }
  e.asyncToArray = h;
  async function m(p) {
    let E = [];
    for await (const w of p)
      E = E.concat(w);
    return E;
  }
  e.asyncToArrayFlat = m;
})(Hi || (Hi = {}));
function r1(e) {
  if (Hi.is(e)) {
    const t = [];
    for (const n of e)
      if (n)
        try {
          n.dispose();
        } catch (r) {
          t.push(r);
        }
    if (t.length === 1)
      throw t[0];
    if (t.length > 1)
      throw new AggregateError(t, "Encountered errors while disposing of store");
    return Array.isArray(e) ? [] : e;
  } else if (e)
    return e.dispose(), e;
}
function Rg(...e) {
  return Yi(() => r1(e));
}
class Pg {
  constructor(t) {
    this._isDisposed = !1, this._fn = t;
  }
  dispose() {
    if (!this._isDisposed) {
      if (!this._fn)
        throw new Error("Unbound disposable context: Need to use an arrow function to preserve the value of this");
      this._isDisposed = !0, this._fn();
    }
  }
}
function Yi(e) {
  return new Pg(e);
}
const va = class va {
  constructor() {
    this._toDispose = /* @__PURE__ */ new Set(), this._isDisposed = !1;
  }
  /**
   * Dispose of all registered disposables and mark this object as disposed.
   *
   * Any future disposables added to this object will be disposed of on `add`.
   */
  dispose() {
    this._isDisposed || (this._isDisposed = !0, this.clear());
  }
  /**
   * @return `true` if this object has been disposed of.
   */
  get isDisposed() {
    return this._isDisposed;
  }
  /**
   * Dispose of all registered disposables but do not mark this object as disposed.
   */
  clear() {
    if (this._toDispose.size !== 0)
      try {
        r1(this._toDispose);
      } finally {
        this._toDispose.clear();
      }
  }
  /**
   * Add a new {@link IDisposable disposable} to the collection.
   */
  add(t) {
    if (!t || t === sr.None)
      return t;
    if (t === this)
      throw new Error("Cannot register a disposable on itself!");
    return this._isDisposed ? va.DISABLE_DISPOSED_WARNING || console.warn(new Error("Trying to add a disposable to a DisposableStore that has already been disposed of. The added object will be leaked!").stack) : this._toDispose.add(t), t;
  }
  /**
   * Deletes a disposable from store and disposes of it. This will not throw or warn and proceed to dispose the
   * disposable even when the disposable is not part in the store.
   */
  delete(t) {
    if (t) {
      if (t === this)
        throw new Error("Cannot dispose a disposable on itself!");
      this._toDispose.delete(t), t.dispose();
    }
  }
};
va.DISABLE_DISPOSED_WARNING = !1;
let Hs = va;
const Xu = class Xu {
  constructor() {
    this._store = new Hs(), this._store;
  }
  dispose() {
    this._store.dispose();
  }
  /**
   * Adds `o` to the collection of disposables managed by this object.
   */
  _register(t) {
    if (t === this)
      throw new Error("Cannot register a disposable on itself!");
    return this._store.add(t);
  }
};
Xu.None = Object.freeze({ dispose() {
} });
let sr = Xu;
const $r = class $r {
  constructor(t) {
    this.element = t, this.next = $r.Undefined, this.prev = $r.Undefined;
  }
};
$r.Undefined = new $r(void 0);
let Fe = $r;
class Ig {
  constructor() {
    this._first = Fe.Undefined, this._last = Fe.Undefined, this._size = 0;
  }
  get size() {
    return this._size;
  }
  isEmpty() {
    return this._first === Fe.Undefined;
  }
  clear() {
    let t = this._first;
    for (; t !== Fe.Undefined; ) {
      const n = t.next;
      t.prev = Fe.Undefined, t.next = Fe.Undefined, t = n;
    }
    this._first = Fe.Undefined, this._last = Fe.Undefined, this._size = 0;
  }
  unshift(t) {
    return this._insert(t, !1);
  }
  push(t) {
    return this._insert(t, !0);
  }
  _insert(t, n) {
    const r = new Fe(t);
    if (this._first === Fe.Undefined)
      this._first = r, this._last = r;
    else if (n) {
      const i = this._last;
      this._last = r, r.prev = i, i.next = r;
    } else {
      const i = this._first;
      this._first = r, r.next = i, i.prev = r;
    }
    this._size += 1;
    let s = !1;
    return () => {
      s || (s = !0, this._remove(r));
    };
  }
  shift() {
    if (this._first !== Fe.Undefined) {
      const t = this._first.element;
      return this._remove(this._first), t;
    }
  }
  pop() {
    if (this._last !== Fe.Undefined) {
      const t = this._last.element;
      return this._remove(this._last), t;
    }
  }
  _remove(t) {
    if (t.prev !== Fe.Undefined && t.next !== Fe.Undefined) {
      const n = t.prev;
      n.next = t.next, t.next.prev = n;
    } else t.prev === Fe.Undefined && t.next === Fe.Undefined ? (this._first = Fe.Undefined, this._last = Fe.Undefined) : t.next === Fe.Undefined ? (this._last = this._last.prev, this._last.next = Fe.Undefined) : t.prev === Fe.Undefined && (this._first = this._first.next, this._first.prev = Fe.Undefined);
    this._size -= 1;
  }
  *[Symbol.iterator]() {
    let t = this._first;
    for (; t !== Fe.Undefined; )
      yield t.element, t = t.next;
  }
}
const $g = globalThis.performance.now.bind(globalThis.performance);
class Aa {
  static create(t) {
    return new Aa(t);
  }
  constructor(t) {
    this._now = t === !1 ? Date.now : $g, this._startTime = this._now(), this._stopTime = -1;
  }
  stop() {
    this._stopTime = this._now();
  }
  reset() {
    this._startTime = this._now(), this._stopTime = -1;
  }
  elapsed() {
    return this._stopTime !== -1 ? this._stopTime - this._startTime : this._now() - this._startTime;
  }
}
var Lo;
(function(e) {
  e.None = () => sr.None;
  function t(A, _) {
    return d(A, () => {
    }, 0, void 0, !0, void 0, _);
  }
  e.defer = t;
  function n(A) {
    return (_, O = null, T) => {
      let P = !1, V;
      return V = A((Y) => {
        if (!P)
          return V ? V.dispose() : P = !0, _.call(O, Y);
      }, null, T), P && V.dispose(), V;
    };
  }
  e.once = n;
  function r(A, _) {
    return e.once(e.filter(A, _));
  }
  e.onceIf = r;
  function s(A, _, O) {
    return f((T, P = null, V) => A((Y) => T.call(P, _(Y)), null, V), O);
  }
  e.map = s;
  function i(A, _, O) {
    return f((T, P = null, V) => A((Y) => {
      _(Y), T.call(P, Y);
    }, null, V), O);
  }
  e.forEach = i;
  function a(A, _, O) {
    return f((T, P = null, V) => A((Y) => _(Y) && T.call(P, Y), null, V), O);
  }
  e.filter = a;
  function o(A) {
    return A;
  }
  e.signal = o;
  function l(...A) {
    return (_, O = null, T) => {
      const P = Rg(...A.map((V) => V((Y) => _.call(O, Y))));
      return c(P, T);
    };
  }
  e.any = l;
  function u(A, _, O, T) {
    let P = O;
    return s(A, (V) => (P = _(P, V), P), T);
  }
  e.reduce = u;
  function f(A, _) {
    let O;
    const T = {
      onWillAddFirstListener() {
        O = A(P.fire, P);
      },
      onDidRemoveLastListener() {
        O?.dispose();
      }
    }, P = new Ht(T);
    return _?.add(P), P.event;
  }
  function c(A, _) {
    return _ instanceof Array ? _.push(A) : _ && _.add(A), A;
  }
  function d(A, _, O = 100, T = !1, P = !1, V, Y) {
    let K, J, $, z = 0, Z;
    const X = {
      leakWarningThreshold: V,
      onWillAddFirstListener() {
        K = A((le) => {
          z++, J = _(J, le), T && !$ && (ne.fire(J), J = void 0), Z = () => {
            const nt = J;
            J = void 0, $ = void 0, (!T || z > 1) && ne.fire(nt), z = 0;
          }, typeof O == "number" ? ($ && clearTimeout($), $ = setTimeout(Z, O)) : $ === void 0 && ($ = null, queueMicrotask(Z));
        });
      },
      onWillRemoveListener() {
        P && z > 0 && Z?.();
      },
      onDidRemoveLastListener() {
        Z = void 0, K.dispose();
      }
    }, ne = new Ht(X);
    return Y?.add(ne), ne.event;
  }
  e.debounce = d;
  function v(A, _ = 0, O) {
    return e.debounce(A, (T, P) => T ? (T.push(P), T) : [P], _, void 0, !0, void 0, O);
  }
  e.accumulate = v;
  function D(A, _ = (T, P) => T === P, O) {
    let T = !0, P;
    return a(A, (V) => {
      const Y = T || !_(V, P);
      return T = !1, P = V, Y;
    }, O);
  }
  e.latch = D;
  function S(A, _, O) {
    return [
      e.filter(A, _, O),
      e.filter(A, (T) => !_(T), O)
    ];
  }
  e.split = S;
  function x(A, _ = !1, O = [], T) {
    let P = O.slice(), V = A((J) => {
      P ? P.push(J) : K.fire(J);
    });
    T && T.add(V);
    const Y = () => {
      P?.forEach((J) => K.fire(J)), P = null;
    }, K = new Ht({
      onWillAddFirstListener() {
        V || (V = A((J) => K.fire(J)), T && T.add(V));
      },
      onDidAddFirstListener() {
        P && (_ ? setTimeout(Y) : Y());
      },
      onDidRemoveLastListener() {
        V && V.dispose(), V = null;
      }
    });
    return T && T.add(K), K.event;
  }
  e.buffer = x;
  function N(A, _) {
    return (T, P, V) => {
      const Y = _(new y());
      return A(function(K) {
        const J = Y.evaluate(K);
        J !== k && T.call(P, J);
      }, void 0, V);
    };
  }
  e.chain = N;
  const k = Symbol("HaltChainable");
  class y {
    constructor() {
      this.steps = [];
    }
    map(_) {
      return this.steps.push(_), this;
    }
    forEach(_) {
      return this.steps.push((O) => (_(O), O)), this;
    }
    filter(_) {
      return this.steps.push((O) => _(O) ? O : k), this;
    }
    reduce(_, O) {
      let T = O;
      return this.steps.push((P) => (T = _(T, P), T)), this;
    }
    latch(_ = (O, T) => O === T) {
      let O = !0, T;
      return this.steps.push((P) => {
        const V = O || !_(P, T);
        return O = !1, T = P, V ? P : k;
      }), this;
    }
    evaluate(_) {
      for (const O of this.steps)
        if (_ = O(_), _ === k)
          break;
      return _;
    }
  }
  function b(A, _, O = (T) => T) {
    const T = (...K) => Y.fire(O(...K)), P = () => A.on(_, T), V = () => A.removeListener(_, T), Y = new Ht({ onWillAddFirstListener: P, onDidRemoveLastListener: V });
    return Y.event;
  }
  e.fromNodeEventEmitter = b;
  function h(A, _, O = (T) => T) {
    const T = (...K) => Y.fire(O(...K)), P = () => A.addEventListener(_, T), V = () => A.removeEventListener(_, T), Y = new Ht({ onWillAddFirstListener: P, onDidRemoveLastListener: V });
    return Y.event;
  }
  e.fromDOMEventEmitter = h;
  function m(A, _) {
    let O;
    const T = new Promise((P, V) => {
      const Y = n(A)(P, null, _);
      O = () => Y.dispose();
    });
    return T.cancel = O, T;
  }
  e.toPromise = m;
  function p(A, _) {
    return A((O) => _.fire(O));
  }
  e.forward = p;
  function E(A, _, O) {
    return _(O), A((T) => _(T));
  }
  e.runAndSubscribe = E;
  class w {
    constructor(_, O) {
      this._observable = _, this._counter = 0, this._hasChanged = !1;
      const T = {
        onWillAddFirstListener: () => {
          _.addObserver(this), this._observable.reportChanges();
        },
        onDidRemoveLastListener: () => {
          _.removeObserver(this);
        }
      };
      this.emitter = new Ht(T), O && O.add(this.emitter);
    }
    beginUpdate(_) {
      this._counter++;
    }
    handlePossibleChange(_) {
    }
    handleChange(_, O) {
      this._hasChanged = !0;
    }
    endUpdate(_) {
      this._counter--, this._counter === 0 && (this._observable.reportChanges(), this._hasChanged && (this._hasChanged = !1, this.emitter.fire(this._observable.get())));
    }
  }
  function L(A, _) {
    return new w(A, _).emitter.event;
  }
  e.fromObservable = L;
  function C(A) {
    return (_, O, T) => {
      let P = 0, V = !1;
      const Y = {
        beginUpdate() {
          P++;
        },
        endUpdate() {
          P--, P === 0 && (A.reportChanges(), V && (V = !1, _.call(O)));
        },
        handlePossibleChange() {
        },
        handleChange() {
          V = !0;
        }
      };
      A.addObserver(Y), A.reportChanges();
      const K = {
        dispose() {
          A.removeObserver(Y);
        }
      };
      return T instanceof Hs ? T.add(K) : Array.isArray(T) && T.push(K), K;
    };
  }
  e.fromObservableLight = C;
})(Lo || (Lo = {}));
const Br = class Br {
  constructor(t) {
    this.listenerCount = 0, this.invocationCount = 0, this.elapsedOverall = 0, this.durations = [], this.name = `${t}_${Br._idPool++}`, Br.all.add(this);
  }
  start(t) {
    this._stopWatch = new Aa(), this.listenerCount = t;
  }
  stop() {
    if (this._stopWatch) {
      const t = this._stopWatch.elapsed();
      this.durations.push(t), this.elapsedOverall += t, this.invocationCount += 1, this._stopWatch = void 0;
    }
  }
};
Br.all = /* @__PURE__ */ new Set(), Br._idPool = 0;
let ko = Br, Bg = -1;
const wa = class wa {
  constructor(t, n, r = (wa._idPool++).toString(16).padStart(3, "0")) {
    this._errorHandler = t, this.threshold = n, this.name = r, this._warnCountdown = 0;
  }
  dispose() {
    this._stacks?.clear();
  }
  check(t, n) {
    const r = this.threshold;
    if (r <= 0 || n < r)
      return;
    this._stacks || (this._stacks = /* @__PURE__ */ new Map());
    const s = this._stacks.get(t.value) || 0;
    if (this._stacks.set(t.value, s + 1), this._warnCountdown -= 1, this._warnCountdown <= 0) {
      this._warnCountdown = r * 0.5;
      const [i, a] = this.getMostFrequentStack(), o = `[${this.name}] potential listener LEAK detected, having ${n} listeners already. MOST frequent listener (${a}):`;
      console.warn(o), console.warn(i);
      const l = new Vg(o, i);
      this._errorHandler(l);
    }
    return () => {
      const i = this._stacks.get(t.value) || 0;
      this._stacks.set(t.value, i - 1);
    };
  }
  getMostFrequentStack() {
    if (!this._stacks)
      return;
    let t, n = 0;
    for (const [r, s] of this._stacks)
      (!t || n < s) && (t = [r, s], n = s);
    return t;
  }
};
wa._idPool = 1;
let Co = wa;
class tu {
  static create() {
    const t = new Error();
    return new tu(t.stack ?? "");
  }
  constructor(t) {
    this.value = t;
  }
  print() {
    console.warn(this.value.split(`
`).slice(2).join(`
`));
  }
}
class Vg extends Error {
  constructor(t, n) {
    super(t), this.name = "ListenerLeakError", this.stack = n;
  }
}
class jg extends Error {
  constructor(t, n) {
    super(t), this.name = "ListenerRefusalError", this.stack = n;
  }
}
class Ya {
  constructor(t) {
    this.value = t;
  }
}
const Ug = 2;
class Ht {
  constructor(t) {
    this._size = 0, this._options = t, this._leakageMon = this._options?.leakWarningThreshold ? new Co(t?.onListenerError ?? Ni, this._options?.leakWarningThreshold ?? Bg) : void 0, this._perfMon = this._options?._profName ? new ko(this._options._profName) : void 0, this._deliveryQueue = this._options?.deliveryQueue;
  }
  dispose() {
    this._disposed || (this._disposed = !0, this._deliveryQueue?.current === this && this._deliveryQueue.reset(), this._listeners && (this._listeners = void 0, this._size = 0), this._options?.onDidRemoveLastListener?.(), this._leakageMon?.dispose());
  }
  /**
   * For the public to allow to subscribe
   * to events from this Emitter
   */
  get event() {
    return this._event ??= (t, n, r) => {
      if (this._leakageMon && this._size > this._leakageMon.threshold ** 2) {
        const o = `[${this._leakageMon.name}] REFUSES to accept new listeners because it exceeded its threshold by far (${this._size} vs ${this._leakageMon.threshold})`;
        console.warn(o);
        const l = this._leakageMon.getMostFrequentStack() ?? ["UNKNOWN stack", -1], u = new jg(`${o}. HINT: Stack shows most frequent listener (${l[1]}-times)`, l[0]);
        return (this._options?.onListenerError || Ni)(u), sr.None;
      }
      if (this._disposed)
        return sr.None;
      n && (t = t.bind(n));
      const s = new Ya(t);
      let i;
      this._leakageMon && this._size >= Math.ceil(this._leakageMon.threshold * 0.2) && (s.stack = tu.create(), i = this._leakageMon.check(s.stack, this._size + 1)), this._listeners ? this._listeners instanceof Ya ? (this._deliveryQueue ??= new qg(), this._listeners = [this._listeners, s]) : this._listeners.push(s) : (this._options?.onWillAddFirstListener?.(this), this._listeners = s, this._options?.onDidAddFirstListener?.(this)), this._options?.onDidAddListener?.(this), this._size++;
      const a = Yi(() => {
        i?.(), this._removeListener(s);
      });
      return r instanceof Hs ? r.add(a) : Array.isArray(r) && r.push(a), a;
    }, this._event;
  }
  _removeListener(t) {
    if (this._options?.onWillRemoveListener?.(this), !this._listeners)
      return;
    if (this._size === 1) {
      this._listeners = void 0, this._options?.onDidRemoveLastListener?.(this), this._size = 0;
      return;
    }
    const n = this._listeners, r = n.indexOf(t);
    if (r === -1)
      throw console.log("disposed?", this._disposed), console.log("size?", this._size), console.log("arr?", JSON.stringify(this._listeners)), new Error("Attempted to dispose unknown listener");
    this._size--, n[r] = void 0;
    const s = this._deliveryQueue.current === this;
    if (this._size * Ug <= n.length) {
      let i = 0;
      for (let a = 0; a < n.length; a++)
        n[a] ? n[i++] = n[a] : s && i < this._deliveryQueue.end && (this._deliveryQueue.end--, i < this._deliveryQueue.i && this._deliveryQueue.i--);
      n.length = i;
    }
  }
  _deliver(t, n) {
    if (!t)
      return;
    const r = this._options?.onListenerError || Ni;
    if (!r) {
      t.value(n);
      return;
    }
    try {
      t.value(n);
    } catch (s) {
      r(s);
    }
  }
  /** Delivers items in the queue. Assumes the queue is ready to go. */
  _deliverQueue(t) {
    const n = t.current._listeners;
    for (; t.i < t.end; )
      this._deliver(n[t.i++], t.value);
    t.reset();
  }
  /**
   * To be kept private to fire an event to
   * subscribers
   */
  fire(t) {
    if (this._deliveryQueue?.current && (this._deliverQueue(this._deliveryQueue), this._perfMon?.stop()), this._perfMon?.start(this._size), this._listeners) if (this._listeners instanceof Ya)
      this._deliver(this._listeners, t);
    else {
      const n = this._deliveryQueue;
      n.enqueue(this, t, this._listeners.length), this._deliverQueue(n);
    }
    this._perfMon?.stop();
  }
  hasListeners() {
    return this._size > 0;
  }
}
class qg {
  constructor() {
    this.i = -1, this.end = 0;
  }
  enqueue(t, n, r) {
    this.i = 0, this.end = r, this.current = t, this.value = n;
  }
  reset() {
    this.i = this.end, this.current = void 0, this.value = void 0;
  }
}
function Wg() {
  return globalThis._VSCODE_NLS_MESSAGES;
}
function s1() {
  return globalThis._VSCODE_NLS_LANGUAGE;
}
const Hg = s1() === "pseudo" || typeof document < "u" && document.location && typeof document.location.hash == "string" && document.location.hash.indexOf("pseudo=true") >= 0;
function ec(e, t) {
  let n;
  return t.length === 0 ? n = e : n = e.replace(/\{(\d+)\}/g, (r, s) => {
    const i = s[0], a = t[i];
    let o = r;
    return typeof a == "string" ? o = a : (typeof a == "number" || typeof a == "boolean" || a === void 0 || a === null) && (o = String(a)), o;
  }), Hg && (n = "［" + n.replace(/[aouei]/g, "$&$&") + "］"), n;
}
function re(e, t, ...n) {
  return ec(typeof e == "number" ? Yg(e, t) : t, n);
}
function Yg(e, t) {
  const n = Wg()?.[e];
  if (typeof n != "string") {
    if (typeof t == "string")
      return t;
    throw new Error(`!!! NLS MISSING: ${e} !!!`);
  }
  return n;
}
const Cr = "en";
let Fo = !1, _o = !1, za = !1, ui, Ga = Cr, tc = Cr, zg, rn;
const er = globalThis;
let ot;
typeof er.vscode < "u" && typeof er.vscode.process < "u" ? ot = er.vscode.process : typeof process < "u" && typeof process?.versions?.node == "string" && (ot = process);
const Gg = typeof ot?.versions?.electron == "string", Jg = Gg && ot?.type === "renderer";
if (typeof ot == "object") {
  Fo = ot.platform === "win32", _o = ot.platform === "darwin", za = ot.platform === "linux", za && ot.env.SNAP && ot.env.SNAP_REVISION, ot.env.CI || ot.env.BUILD_ARTIFACTSTAGINGDIRECTORY || ot.env.GITHUB_WORKSPACE, ui = Cr, Ga = Cr;
  const e = ot.env.VSCODE_NLS_CONFIG;
  if (e)
    try {
      const t = JSON.parse(e);
      ui = t.userLocale, tc = t.osLocale, Ga = t.resolvedLanguage || Cr, zg = t.languagePack?.translationsConfigFile;
    } catch {
    }
} else typeof navigator == "object" && !Jg ? (rn = navigator.userAgent, Fo = rn.indexOf("Windows") >= 0, _o = rn.indexOf("Macintosh") >= 0, (rn.indexOf("Macintosh") >= 0 || rn.indexOf("iPad") >= 0 || rn.indexOf("iPhone") >= 0) && navigator.maxTouchPoints && navigator.maxTouchPoints > 0, za = rn.indexOf("Linux") >= 0, rn?.indexOf("Mobi") >= 0, Ga = s1() || Cr, ui = navigator.language.toLowerCase(), tc = ui) : console.error("Unable to resolve platform.");
const Ys = Fo, Qg = _o, Jt = rn, Kg = typeof er.postMessage == "function" && !er.importScripts;
(() => {
  if (Kg) {
    const e = [];
    er.addEventListener("message", (n) => {
      if (n.data && n.data.vscodeScheduleAsyncWork)
        for (let r = 0, s = e.length; r < s; r++) {
          const i = e[r];
          if (i.id === n.data.vscodeScheduleAsyncWork) {
            e.splice(r, 1), i.callback();
            return;
          }
        }
    });
    let t = 0;
    return (n) => {
      const r = ++t;
      e.push({
        id: r,
        callback: n
      }), er.postMessage({ vscodeScheduleAsyncWork: r }, "*");
    };
  }
  return (e) => setTimeout(e);
})();
const Xg = !!(Jt && Jt.indexOf("Chrome") >= 0);
Jt && Jt.indexOf("Firefox") >= 0;
!Xg && Jt && Jt.indexOf("Safari") >= 0;
Jt && Jt.indexOf("Edg/") >= 0;
Jt && Jt.indexOf("Android") >= 0;
function Zg(e) {
  return e;
}
class e0 {
  constructor(t, n) {
    this.lastCache = void 0, this.lastArgKey = void 0, typeof t == "function" ? (this._fn = t, this._computeKey = Zg) : (this._fn = n, this._computeKey = t.getCacheKey);
  }
  get(t) {
    const n = this._computeKey(t);
    return this.lastArgKey !== n && (this.lastArgKey = n, this.lastCache = this._fn(t)), this.lastCache;
  }
}
var zn;
(function(e) {
  e[e.Uninitialized = 0] = "Uninitialized", e[e.Running = 1] = "Running", e[e.Completed = 2] = "Completed";
})(zn || (zn = {}));
class To {
  constructor(t) {
    this.executor = t, this._state = zn.Uninitialized;
  }
  /**
   * Get the wrapped value.
   *
   * This will force evaluation of the lazy value if it has not been resolved yet. Lazy values are only
   * resolved once. `getValue` will re-throw exceptions that are hit while resolving the value
   */
  get value() {
    if (this._state === zn.Uninitialized) {
      this._state = zn.Running;
      try {
        this._value = this.executor();
      } catch (t) {
        this._error = t;
      } finally {
        this._state = zn.Completed;
      }
    } else if (this._state === zn.Running)
      throw new Error("Cannot read the value of a lazy that is being initialized");
    if (this._error)
      throw this._error;
    return this._value;
  }
  /**
   * Get the wrapped value without forcing evaluation.
   */
  get rawValue() {
    return this._value;
  }
}
function t0(e) {
  return e.replace(/[\\\{\}\*\+\?\|\^\$\.\[\]\(\)]/g, "\\$&");
}
function n0(e) {
  return e.source === "^" || e.source === "^$" || e.source === "$" || e.source === "^\\s*$" ? !1 : !!(e.exec("") && e.lastIndex === 0);
}
function r0(e) {
  return e.split(/\r\n|\r|\n/);
}
function s0(e) {
  for (let t = 0, n = e.length; t < n; t++) {
    const r = e.charCodeAt(t);
    if (r !== 32 && r !== 9)
      return t;
  }
  return -1;
}
function i0(e, t = e.length - 1) {
  for (let n = t; n >= 0; n--) {
    const r = e.charCodeAt(n);
    if (r !== 32 && r !== 9)
      return n;
  }
  return -1;
}
function i1(e) {
  return e >= 65 && e <= 90;
}
function a0(e, t) {
  const n = Math.min(e.length, t.length);
  let r;
  for (r = 0; r < n; r++)
    if (e.charCodeAt(r) !== t.charCodeAt(r))
      return r;
  return n;
}
function o0(e, t) {
  const n = Math.min(e.length, t.length);
  let r;
  const s = e.length - 1, i = t.length - 1;
  for (r = 0; r < n; r++)
    if (e.charCodeAt(s - r) !== t.charCodeAt(i - r))
      return r;
  return n;
}
function Mo(e) {
  return 55296 <= e && e <= 56319;
}
function l0(e) {
  return 56320 <= e && e <= 57343;
}
function u0(e, t) {
  return (e - 55296 << 10) + (t - 56320) + 65536;
}
function c0(e, t, n) {
  const r = e.charCodeAt(n);
  if (Mo(r) && n + 1 < t) {
    const s = e.charCodeAt(n + 1);
    if (l0(s))
      return u0(r, s);
  }
  return r;
}
const f0 = /^[\t\n\r\x20-\x7E]*$/;
function h0(e) {
  return f0.test(e);
}
const Wt = class Wt {
  static getInstance(t) {
    return Wt.cache.get(Array.from(t));
  }
  static getLocales() {
    return Wt._locales.value;
  }
  constructor(t) {
    this.confusableDictionary = t;
  }
  isAmbiguous(t) {
    return this.confusableDictionary.has(t);
  }
  /**
   * Returns the non basic ASCII code point that the given code point can be confused,
   * or undefined if such code point does note exist.
   */
  getPrimaryConfusable(t) {
    return this.confusableDictionary.get(t);
  }
  getConfusableCodePoints() {
    return new Set(this.confusableDictionary.keys());
  }
};
Wt.ambiguousCharacterData = new To(() => JSON.parse('{"_common":[8232,32,8233,32,5760,32,8192,32,8193,32,8194,32,8195,32,8196,32,8197,32,8198,32,8200,32,8201,32,8202,32,8287,32,8199,32,8239,32,2042,95,65101,95,65102,95,65103,95,8208,45,8209,45,8210,45,65112,45,1748,45,8259,45,727,45,8722,45,10134,45,11450,45,1549,44,1643,44,184,44,42233,44,894,59,2307,58,2691,58,1417,58,1795,58,1796,58,5868,58,65072,58,6147,58,6153,58,8282,58,1475,58,760,58,42889,58,8758,58,720,58,42237,58,451,33,11601,33,660,63,577,63,2429,63,5038,63,42731,63,119149,46,8228,46,1793,46,1794,46,42510,46,68176,46,1632,46,1776,46,42232,46,1373,96,65287,96,8219,96,1523,96,8242,96,1370,96,8175,96,65344,96,900,96,8189,96,8125,96,8127,96,8190,96,697,96,884,96,712,96,714,96,715,96,756,96,699,96,701,96,700,96,702,96,42892,96,1497,96,2036,96,2037,96,5194,96,5836,96,94033,96,94034,96,65339,91,10088,40,10098,40,12308,40,64830,40,65341,93,10089,41,10099,41,12309,41,64831,41,10100,123,119060,123,10101,125,65342,94,8270,42,1645,42,8727,42,66335,42,5941,47,8257,47,8725,47,8260,47,9585,47,10187,47,10744,47,119354,47,12755,47,12339,47,11462,47,20031,47,12035,47,65340,92,65128,92,8726,92,10189,92,10741,92,10745,92,119311,92,119355,92,12756,92,20022,92,12034,92,42872,38,708,94,710,94,5869,43,10133,43,66203,43,8249,60,10094,60,706,60,119350,60,5176,60,5810,60,5120,61,11840,61,12448,61,42239,61,8250,62,10095,62,707,62,119351,62,5171,62,94015,62,8275,126,732,126,8128,126,8764,126,65372,124,65293,45,118002,50,120784,50,120794,50,120804,50,120814,50,120824,50,130034,50,42842,50,423,50,1000,50,42564,50,5311,50,42735,50,119302,51,118003,51,120785,51,120795,51,120805,51,120815,51,120825,51,130035,51,42923,51,540,51,439,51,42858,51,11468,51,1248,51,94011,51,71882,51,118004,52,120786,52,120796,52,120806,52,120816,52,120826,52,130036,52,5070,52,71855,52,118005,53,120787,53,120797,53,120807,53,120817,53,120827,53,130037,53,444,53,71867,53,118006,54,120788,54,120798,54,120808,54,120818,54,120828,54,130038,54,11474,54,5102,54,71893,54,119314,55,118007,55,120789,55,120799,55,120809,55,120819,55,120829,55,130039,55,66770,55,71878,55,2819,56,2538,56,2666,56,125131,56,118008,56,120790,56,120800,56,120810,56,120820,56,120830,56,130040,56,547,56,546,56,66330,56,2663,57,2920,57,2541,57,3437,57,118009,57,120791,57,120801,57,120811,57,120821,57,120831,57,130041,57,42862,57,11466,57,71884,57,71852,57,71894,57,9082,97,65345,97,119834,97,119886,97,119938,97,119990,97,120042,97,120094,97,120146,97,120198,97,120250,97,120302,97,120354,97,120406,97,120458,97,593,97,945,97,120514,97,120572,97,120630,97,120688,97,120746,97,65313,65,117974,65,119808,65,119860,65,119912,65,119964,65,120016,65,120068,65,120120,65,120172,65,120224,65,120276,65,120328,65,120380,65,120432,65,913,65,120488,65,120546,65,120604,65,120662,65,120720,65,5034,65,5573,65,42222,65,94016,65,66208,65,119835,98,119887,98,119939,98,119991,98,120043,98,120095,98,120147,98,120199,98,120251,98,120303,98,120355,98,120407,98,120459,98,388,98,5071,98,5234,98,5551,98,65314,66,8492,66,117975,66,119809,66,119861,66,119913,66,120017,66,120069,66,120121,66,120173,66,120225,66,120277,66,120329,66,120381,66,120433,66,42932,66,914,66,120489,66,120547,66,120605,66,120663,66,120721,66,5108,66,5623,66,42192,66,66178,66,66209,66,66305,66,65347,99,8573,99,119836,99,119888,99,119940,99,119992,99,120044,99,120096,99,120148,99,120200,99,120252,99,120304,99,120356,99,120408,99,120460,99,7428,99,1010,99,11429,99,43951,99,66621,99,128844,67,71913,67,71922,67,65315,67,8557,67,8450,67,8493,67,117976,67,119810,67,119862,67,119914,67,119966,67,120018,67,120174,67,120226,67,120278,67,120330,67,120382,67,120434,67,1017,67,11428,67,5087,67,42202,67,66210,67,66306,67,66581,67,66844,67,8574,100,8518,100,119837,100,119889,100,119941,100,119993,100,120045,100,120097,100,120149,100,120201,100,120253,100,120305,100,120357,100,120409,100,120461,100,1281,100,5095,100,5231,100,42194,100,8558,68,8517,68,117977,68,119811,68,119863,68,119915,68,119967,68,120019,68,120071,68,120123,68,120175,68,120227,68,120279,68,120331,68,120383,68,120435,68,5024,68,5598,68,5610,68,42195,68,8494,101,65349,101,8495,101,8519,101,119838,101,119890,101,119942,101,120046,101,120098,101,120150,101,120202,101,120254,101,120306,101,120358,101,120410,101,120462,101,43826,101,1213,101,8959,69,65317,69,8496,69,117978,69,119812,69,119864,69,119916,69,120020,69,120072,69,120124,69,120176,69,120228,69,120280,69,120332,69,120384,69,120436,69,917,69,120492,69,120550,69,120608,69,120666,69,120724,69,11577,69,5036,69,42224,69,71846,69,71854,69,66182,69,119839,102,119891,102,119943,102,119995,102,120047,102,120099,102,120151,102,120203,102,120255,102,120307,102,120359,102,120411,102,120463,102,43829,102,42905,102,383,102,7837,102,1412,102,119315,70,8497,70,117979,70,119813,70,119865,70,119917,70,120021,70,120073,70,120125,70,120177,70,120229,70,120281,70,120333,70,120385,70,120437,70,42904,70,988,70,120778,70,5556,70,42205,70,71874,70,71842,70,66183,70,66213,70,66853,70,65351,103,8458,103,119840,103,119892,103,119944,103,120048,103,120100,103,120152,103,120204,103,120256,103,120308,103,120360,103,120412,103,120464,103,609,103,7555,103,397,103,1409,103,117980,71,119814,71,119866,71,119918,71,119970,71,120022,71,120074,71,120126,71,120178,71,120230,71,120282,71,120334,71,120386,71,120438,71,1292,71,5056,71,5107,71,42198,71,65352,104,8462,104,119841,104,119945,104,119997,104,120049,104,120101,104,120153,104,120205,104,120257,104,120309,104,120361,104,120413,104,120465,104,1211,104,1392,104,5058,104,65320,72,8459,72,8460,72,8461,72,117981,72,119815,72,119867,72,119919,72,120023,72,120179,72,120231,72,120283,72,120335,72,120387,72,120439,72,919,72,120494,72,120552,72,120610,72,120668,72,120726,72,11406,72,5051,72,5500,72,42215,72,66255,72,731,105,9075,105,65353,105,8560,105,8505,105,8520,105,119842,105,119894,105,119946,105,119998,105,120050,105,120102,105,120154,105,120206,105,120258,105,120310,105,120362,105,120414,105,120466,105,120484,105,618,105,617,105,953,105,8126,105,890,105,120522,105,120580,105,120638,105,120696,105,120754,105,1110,105,42567,105,1231,105,43893,105,5029,105,71875,105,65354,106,8521,106,119843,106,119895,106,119947,106,119999,106,120051,106,120103,106,120155,106,120207,106,120259,106,120311,106,120363,106,120415,106,120467,106,1011,106,1112,106,65322,74,117983,74,119817,74,119869,74,119921,74,119973,74,120025,74,120077,74,120129,74,120181,74,120233,74,120285,74,120337,74,120389,74,120441,74,42930,74,895,74,1032,74,5035,74,5261,74,42201,74,119844,107,119896,107,119948,107,120000,107,120052,107,120104,107,120156,107,120208,107,120260,107,120312,107,120364,107,120416,107,120468,107,8490,75,65323,75,117984,75,119818,75,119870,75,119922,75,119974,75,120026,75,120078,75,120130,75,120182,75,120234,75,120286,75,120338,75,120390,75,120442,75,922,75,120497,75,120555,75,120613,75,120671,75,120729,75,11412,75,5094,75,5845,75,42199,75,66840,75,1472,108,8739,73,9213,73,65512,73,1633,108,1777,73,66336,108,125127,108,118001,108,120783,73,120793,73,120803,73,120813,73,120823,73,130033,73,65321,73,8544,73,8464,73,8465,73,117982,108,119816,73,119868,73,119920,73,120024,73,120128,73,120180,73,120232,73,120284,73,120336,73,120388,73,120440,73,65356,108,8572,73,8467,108,119845,108,119897,108,119949,108,120001,108,120053,108,120105,73,120157,73,120209,73,120261,73,120313,73,120365,73,120417,73,120469,73,448,73,120496,73,120554,73,120612,73,120670,73,120728,73,11410,73,1030,73,1216,73,1493,108,1503,108,1575,108,126464,108,126592,108,65166,108,65165,108,1994,108,11599,73,5825,73,42226,73,93992,73,66186,124,66313,124,119338,76,8556,76,8466,76,117985,76,119819,76,119871,76,119923,76,120027,76,120079,76,120131,76,120183,76,120235,76,120287,76,120339,76,120391,76,120443,76,11472,76,5086,76,5290,76,42209,76,93974,76,71843,76,71858,76,66587,76,66854,76,65325,77,8559,77,8499,77,117986,77,119820,77,119872,77,119924,77,120028,77,120080,77,120132,77,120184,77,120236,77,120288,77,120340,77,120392,77,120444,77,924,77,120499,77,120557,77,120615,77,120673,77,120731,77,1018,77,11416,77,5047,77,5616,77,5846,77,42207,77,66224,77,66321,77,119847,110,119899,110,119951,110,120003,110,120055,110,120107,110,120159,110,120211,110,120263,110,120315,110,120367,110,120419,110,120471,110,1400,110,1404,110,65326,78,8469,78,117987,78,119821,78,119873,78,119925,78,119977,78,120029,78,120081,78,120185,78,120237,78,120289,78,120341,78,120393,78,120445,78,925,78,120500,78,120558,78,120616,78,120674,78,120732,78,11418,78,42208,78,66835,78,3074,111,3202,111,3330,111,3458,111,2406,111,2662,111,2790,111,3046,111,3174,111,3302,111,3430,111,3664,111,3792,111,4160,111,1637,111,1781,111,65359,111,8500,111,119848,111,119900,111,119952,111,120056,111,120108,111,120160,111,120212,111,120264,111,120316,111,120368,111,120420,111,120472,111,7439,111,7441,111,43837,111,959,111,120528,111,120586,111,120644,111,120702,111,120760,111,963,111,120532,111,120590,111,120648,111,120706,111,120764,111,11423,111,4351,111,1413,111,1505,111,1607,111,126500,111,126564,111,126596,111,65259,111,65260,111,65258,111,65257,111,1726,111,64428,111,64429,111,64427,111,64426,111,1729,111,64424,111,64425,111,64423,111,64422,111,1749,111,3360,111,4125,111,66794,111,71880,111,71895,111,66604,111,1984,79,2534,79,2918,79,12295,79,70864,79,71904,79,118000,79,120782,79,120792,79,120802,79,120812,79,120822,79,130032,79,65327,79,117988,79,119822,79,119874,79,119926,79,119978,79,120030,79,120082,79,120134,79,120186,79,120238,79,120290,79,120342,79,120394,79,120446,79,927,79,120502,79,120560,79,120618,79,120676,79,120734,79,11422,79,1365,79,11604,79,4816,79,2848,79,66754,79,42227,79,71861,79,66194,79,66219,79,66564,79,66838,79,9076,112,65360,112,119849,112,119901,112,119953,112,120005,112,120057,112,120109,112,120161,112,120213,112,120265,112,120317,112,120369,112,120421,112,120473,112,961,112,120530,112,120544,112,120588,112,120602,112,120646,112,120660,112,120704,112,120718,112,120762,112,120776,112,11427,112,65328,80,8473,80,117989,80,119823,80,119875,80,119927,80,119979,80,120031,80,120083,80,120187,80,120239,80,120291,80,120343,80,120395,80,120447,80,929,80,120504,80,120562,80,120620,80,120678,80,120736,80,11426,80,5090,80,5229,80,42193,80,66197,80,119850,113,119902,113,119954,113,120006,113,120058,113,120110,113,120162,113,120214,113,120266,113,120318,113,120370,113,120422,113,120474,113,1307,113,1379,113,1382,113,8474,81,117990,81,119824,81,119876,81,119928,81,119980,81,120032,81,120084,81,120188,81,120240,81,120292,81,120344,81,120396,81,120448,81,11605,81,119851,114,119903,114,119955,114,120007,114,120059,114,120111,114,120163,114,120215,114,120267,114,120319,114,120371,114,120423,114,120475,114,43847,114,43848,114,7462,114,11397,114,43905,114,119318,82,8475,82,8476,82,8477,82,117991,82,119825,82,119877,82,119929,82,120033,82,120189,82,120241,82,120293,82,120345,82,120397,82,120449,82,422,82,5025,82,5074,82,66740,82,5511,82,42211,82,94005,82,65363,115,119852,115,119904,115,119956,115,120008,115,120060,115,120112,115,120164,115,120216,115,120268,115,120320,115,120372,115,120424,115,120476,115,42801,115,445,115,1109,115,43946,115,71873,115,66632,115,65331,83,117992,83,119826,83,119878,83,119930,83,119982,83,120034,83,120086,83,120138,83,120190,83,120242,83,120294,83,120346,83,120398,83,120450,83,1029,83,1359,83,5077,83,5082,83,42210,83,94010,83,66198,83,66592,83,119853,116,119905,116,119957,116,120009,116,120061,116,120113,116,120165,116,120217,116,120269,116,120321,116,120373,116,120425,116,120477,116,8868,84,10201,84,128872,84,65332,84,117993,84,119827,84,119879,84,119931,84,119983,84,120035,84,120087,84,120139,84,120191,84,120243,84,120295,84,120347,84,120399,84,120451,84,932,84,120507,84,120565,84,120623,84,120681,84,120739,84,11430,84,5026,84,42196,84,93962,84,71868,84,66199,84,66225,84,66325,84,119854,117,119906,117,119958,117,120010,117,120062,117,120114,117,120166,117,120218,117,120270,117,120322,117,120374,117,120426,117,120478,117,42911,117,7452,117,43854,117,43858,117,651,117,965,117,120534,117,120592,117,120650,117,120708,117,120766,117,1405,117,66806,117,71896,117,8746,85,8899,85,117994,85,119828,85,119880,85,119932,85,119984,85,120036,85,120088,85,120140,85,120192,85,120244,85,120296,85,120348,85,120400,85,120452,85,1357,85,4608,85,66766,85,5196,85,42228,85,94018,85,71864,85,8744,118,8897,118,65366,118,8564,118,119855,118,119907,118,119959,118,120011,118,120063,118,120115,118,120167,118,120219,118,120271,118,120323,118,120375,118,120427,118,120479,118,7456,118,957,118,120526,118,120584,118,120642,118,120700,118,120758,118,1141,118,1496,118,71430,118,43945,118,71872,118,119309,86,1639,86,1783,86,8548,86,117995,86,119829,86,119881,86,119933,86,119985,86,120037,86,120089,86,120141,86,120193,86,120245,86,120297,86,120349,86,120401,86,120453,86,1140,86,11576,86,5081,86,5167,86,42719,86,42214,86,93960,86,71840,86,66845,86,623,119,119856,119,119908,119,119960,119,120012,119,120064,119,120116,119,120168,119,120220,119,120272,119,120324,119,120376,119,120428,119,120480,119,7457,119,1121,119,1309,119,1377,119,71434,119,71438,119,71439,119,43907,119,71910,87,71919,87,117996,87,119830,87,119882,87,119934,87,119986,87,120038,87,120090,87,120142,87,120194,87,120246,87,120298,87,120350,87,120402,87,120454,87,1308,87,5043,87,5076,87,42218,87,5742,120,10539,120,10540,120,10799,120,65368,120,8569,120,119857,120,119909,120,119961,120,120013,120,120065,120,120117,120,120169,120,120221,120,120273,120,120325,120,120377,120,120429,120,120481,120,5441,120,5501,120,5741,88,9587,88,66338,88,71916,88,65336,88,8553,88,117997,88,119831,88,119883,88,119935,88,119987,88,120039,88,120091,88,120143,88,120195,88,120247,88,120299,88,120351,88,120403,88,120455,88,42931,88,935,88,120510,88,120568,88,120626,88,120684,88,120742,88,11436,88,11613,88,5815,88,42219,88,66192,88,66228,88,66327,88,66855,88,611,121,7564,121,65369,121,119858,121,119910,121,119962,121,120014,121,120066,121,120118,121,120170,121,120222,121,120274,121,120326,121,120378,121,120430,121,120482,121,655,121,7935,121,43866,121,947,121,8509,121,120516,121,120574,121,120632,121,120690,121,120748,121,1199,121,4327,121,71900,121,65337,89,117998,89,119832,89,119884,89,119936,89,119988,89,120040,89,120092,89,120144,89,120196,89,120248,89,120300,89,120352,89,120404,89,120456,89,933,89,978,89,120508,89,120566,89,120624,89,120682,89,120740,89,11432,89,1198,89,5033,89,5053,89,42220,89,94019,89,71844,89,66226,89,119859,122,119911,122,119963,122,120015,122,120067,122,120119,122,120171,122,120223,122,120275,122,120327,122,120379,122,120431,122,120483,122,7458,122,43923,122,71876,122,71909,90,66293,90,65338,90,8484,90,8488,90,117999,90,119833,90,119885,90,119937,90,119989,90,120041,90,120197,90,120249,90,120301,90,120353,90,120405,90,120457,90,918,90,120493,90,120551,90,120609,90,120667,90,120725,90,5059,90,42204,90,71849,90,65282,34,65283,35,65284,36,65285,37,65286,38,65290,42,65291,43,65294,46,65295,47,65296,48,65298,50,65299,51,65300,52,65301,53,65302,54,65303,55,65304,56,65305,57,65308,60,65309,61,65310,62,65312,64,65316,68,65318,70,65319,71,65324,76,65329,81,65330,82,65333,85,65334,86,65335,87,65343,95,65346,98,65348,100,65350,102,65355,107,65357,109,65358,110,65361,113,65362,114,65364,116,65365,117,65367,119,65370,122,65371,123,65373,125,119846,109],"_default":[160,32,8211,45,65374,126,8218,44,65306,58,65281,33,8216,96,8217,96,8245,96,180,96,12494,47,1047,51,1073,54,1072,97,1040,65,1068,98,1042,66,1089,99,1057,67,1077,101,1045,69,1053,72,305,105,1050,75,921,73,1052,77,1086,111,1054,79,1009,112,1088,112,1056,80,1075,114,1058,84,215,120,1093,120,1061,88,1091,121,1059,89,65288,40,65289,41,65292,44,65297,49,65307,59,65311,63],"cs":[65374,126,8218,44,65306,58,65281,33,8216,96,8245,96,180,96,12494,47,1047,51,1073,54,1072,97,1040,65,1068,98,1042,66,1089,99,1057,67,1077,101,1045,69,1053,72,305,105,1050,75,921,73,1052,77,1086,111,1054,79,1009,112,1088,112,1056,80,1075,114,1058,84,1093,120,1061,88,1091,121,1059,89,65288,40,65289,41,65292,44,65297,49,65307,59,65311,63],"de":[65374,126,65306,58,65281,33,8245,96,180,96,12494,47,1047,51,1073,54,1072,97,1040,65,1068,98,1042,66,1089,99,1057,67,1077,101,1045,69,1053,72,305,105,1050,75,921,73,1052,77,1086,111,1054,79,1009,112,1088,112,1056,80,1075,114,1058,84,1093,120,1061,88,1091,121,1059,89,65288,40,65289,41,65292,44,65297,49,65307,59,65311,63],"es":[8211,45,65374,126,8218,44,65306,58,65281,33,8245,96,180,96,12494,47,1047,51,1073,54,1072,97,1040,65,1068,98,1042,66,1089,99,1057,67,1077,101,1045,69,1053,72,305,105,1050,75,1052,77,1086,111,1054,79,1009,112,1088,112,1056,80,1075,114,1058,84,215,120,1093,120,1061,88,1091,121,1059,89,65288,40,65289,41,65292,44,65297,49,65307,59,65311,63],"fr":[65374,126,8218,44,65306,58,65281,33,8216,96,8245,96,12494,47,1047,51,1073,54,1072,97,1040,65,1068,98,1042,66,1089,99,1057,67,1077,101,1045,69,1053,72,305,105,1050,75,921,73,1052,77,1086,111,1054,79,1009,112,1088,112,1056,80,1075,114,1058,84,215,120,1093,120,1061,88,1091,121,1059,89,65288,40,65289,41,65292,44,65297,49,65307,59,65311,63],"it":[160,32,8211,45,65374,126,8218,44,65306,58,65281,33,8245,96,180,96,12494,47,1047,51,1073,54,1072,97,1040,65,1068,98,1042,66,1089,99,1057,67,1077,101,1045,69,1053,72,305,105,1050,75,921,73,1052,77,1086,111,1054,79,1009,112,1088,112,1056,80,1075,114,1058,84,215,120,1093,120,1061,88,1091,121,1059,89,65288,40,65289,41,65292,44,65297,49,65307,59,65311,63],"ja":[8211,45,8218,44,65281,33,8216,96,8245,96,180,96,1047,51,1073,54,1072,97,1040,65,1068,98,1042,66,1089,99,1057,67,1077,101,1045,69,1053,72,305,105,1050,75,921,73,1052,77,1086,111,1054,79,1009,112,1088,112,1056,80,1075,114,1058,84,215,120,1093,120,1061,88,1091,121,1059,89,65292,44,65297,49,65307,59],"ko":[8211,45,65374,126,8218,44,65306,58,65281,33,8245,96,180,96,12494,47,1047,51,1073,54,1072,97,1040,65,1068,98,1042,66,1089,99,1057,67,1077,101,1045,69,1053,72,305,105,1050,75,921,73,1052,77,1086,111,1054,79,1009,112,1088,112,1056,80,1075,114,1058,84,215,120,1093,120,1061,88,1091,121,1059,89,65288,40,65289,41,65292,44,65297,49,65307,59,65311,63],"pl":[65374,126,65306,58,65281,33,8216,96,8245,96,180,96,12494,47,1047,51,1073,54,1072,97,1040,65,1068,98,1042,66,1089,99,1057,67,1077,101,1045,69,1053,72,305,105,1050,75,921,73,1052,77,1086,111,1054,79,1009,112,1088,112,1056,80,1075,114,1058,84,215,120,1093,120,1061,88,1091,121,1059,89,65288,40,65289,41,65292,44,65297,49,65307,59,65311,63],"pt-BR":[65374,126,8218,44,65306,58,65281,33,8216,96,8245,96,180,96,12494,47,1047,51,1073,54,1072,97,1040,65,1068,98,1042,66,1089,99,1057,67,1077,101,1045,69,1053,72,305,105,1050,75,921,73,1052,77,1086,111,1054,79,1009,112,1088,112,1056,80,1075,114,1058,84,215,120,1093,120,1061,88,1091,121,1059,89,65288,40,65289,41,65292,44,65297,49,65307,59,65311,63],"qps-ploc":[160,32,8211,45,65374,126,8218,44,65306,58,65281,33,8216,96,8245,96,180,96,12494,47,1047,51,1073,54,1072,97,1040,65,1068,98,1042,66,1089,99,1057,67,1077,101,1045,69,1053,72,305,105,1050,75,921,73,1052,77,1086,111,1054,79,1088,112,1056,80,1075,114,1058,84,215,120,1093,120,1061,88,1091,121,1059,89,65288,40,65289,41,65292,44,65297,49,65307,59,65311,63],"ru":[65374,126,8218,44,65306,58,65281,33,8216,96,8245,96,180,96,12494,47,305,105,921,73,1009,112,215,120,65288,40,65289,41,65292,44,65297,49,65307,59,65311,63],"tr":[160,32,8211,45,65374,126,8218,44,65306,58,65281,33,8245,96,180,96,12494,47,1047,51,1073,54,1072,97,1040,65,1068,98,1042,66,1089,99,1057,67,1077,101,1045,69,1053,72,1050,75,921,73,1052,77,1086,111,1054,79,1009,112,1088,112,1056,80,1075,114,1058,84,215,120,1093,120,1061,88,1091,121,1059,89,65288,40,65289,41,65292,44,65297,49,65307,59,65311,63],"zh-hans":[160,32,65374,126,8218,44,8245,96,180,96,12494,47,1047,51,1073,54,1072,97,1040,65,1068,98,1042,66,1089,99,1057,67,1077,101,1045,69,1053,72,305,105,1050,75,921,73,1052,77,1086,111,1054,79,1009,112,1088,112,1056,80,1075,114,1058,84,215,120,1093,120,1061,88,1091,121,1059,89,65297,49],"zh-hant":[8211,45,65374,126,8218,44,180,96,12494,47,1047,51,1073,54,1072,97,1040,65,1068,98,1042,66,1089,99,1057,67,1077,101,1045,69,1053,72,305,105,1050,75,921,73,1052,77,1086,111,1054,79,1009,112,1088,112,1056,80,1075,114,1058,84,215,120,1093,120,1061,88,1091,121,1059,89]}')), Wt.cache = new e0({ getCacheKey: JSON.stringify }, (t) => {
  function n(f) {
    const c = /* @__PURE__ */ new Map();
    for (let d = 0; d < f.length; d += 2)
      c.set(f[d], f[d + 1]);
    return c;
  }
  function r(f, c) {
    const d = new Map(f);
    for (const [v, D] of c)
      d.set(v, D);
    return d;
  }
  function s(f, c) {
    if (!f)
      return c;
    const d = /* @__PURE__ */ new Map();
    for (const [v, D] of f)
      c.has(v) && d.set(v, D);
    return d;
  }
  const i = Wt.ambiguousCharacterData.value;
  let a = t.filter((f) => !f.startsWith("_") && f in i);
  a.length === 0 && (a = ["_default"]);
  let o;
  for (const f of a) {
    const c = n(i[f]);
    o = s(o, c);
  }
  const l = n(i._common), u = r(l, o);
  return new Wt(u);
}), Wt._locales = new To(() => Object.keys(Wt.ambiguousCharacterData.value).filter((t) => !t.startsWith("_")));
let zs = Wt;
const Vr = class Vr {
  static getRawData() {
    return JSON.parse('{"_common":[11,12,13,127,847,1564,4447,4448,6068,6069,6155,6156,6157,6158,7355,7356,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8204,8205,8206,8207,8234,8235,8236,8237,8238,8239,8287,8288,8289,8290,8291,8292,8293,8294,8295,8296,8297,8298,8299,8300,8301,8302,8303,10240,12644,65024,65025,65026,65027,65028,65029,65030,65031,65032,65033,65034,65035,65036,65037,65038,65039,65279,65440,65520,65521,65522,65523,65524,65525,65526,65527,65528,65532,78844,119155,119156,119157,119158,119159,119160,119161,119162,917504,917505,917506,917507,917508,917509,917510,917511,917512,917513,917514,917515,917516,917517,917518,917519,917520,917521,917522,917523,917524,917525,917526,917527,917528,917529,917530,917531,917532,917533,917534,917535,917536,917537,917538,917539,917540,917541,917542,917543,917544,917545,917546,917547,917548,917549,917550,917551,917552,917553,917554,917555,917556,917557,917558,917559,917560,917561,917562,917563,917564,917565,917566,917567,917568,917569,917570,917571,917572,917573,917574,917575,917576,917577,917578,917579,917580,917581,917582,917583,917584,917585,917586,917587,917588,917589,917590,917591,917592,917593,917594,917595,917596,917597,917598,917599,917600,917601,917602,917603,917604,917605,917606,917607,917608,917609,917610,917611,917612,917613,917614,917615,917616,917617,917618,917619,917620,917621,917622,917623,917624,917625,917626,917627,917628,917629,917630,917631,917760,917761,917762,917763,917764,917765,917766,917767,917768,917769,917770,917771,917772,917773,917774,917775,917776,917777,917778,917779,917780,917781,917782,917783,917784,917785,917786,917787,917788,917789,917790,917791,917792,917793,917794,917795,917796,917797,917798,917799,917800,917801,917802,917803,917804,917805,917806,917807,917808,917809,917810,917811,917812,917813,917814,917815,917816,917817,917818,917819,917820,917821,917822,917823,917824,917825,917826,917827,917828,917829,917830,917831,917832,917833,917834,917835,917836,917837,917838,917839,917840,917841,917842,917843,917844,917845,917846,917847,917848,917849,917850,917851,917852,917853,917854,917855,917856,917857,917858,917859,917860,917861,917862,917863,917864,917865,917866,917867,917868,917869,917870,917871,917872,917873,917874,917875,917876,917877,917878,917879,917880,917881,917882,917883,917884,917885,917886,917887,917888,917889,917890,917891,917892,917893,917894,917895,917896,917897,917898,917899,917900,917901,917902,917903,917904,917905,917906,917907,917908,917909,917910,917911,917912,917913,917914,917915,917916,917917,917918,917919,917920,917921,917922,917923,917924,917925,917926,917927,917928,917929,917930,917931,917932,917933,917934,917935,917936,917937,917938,917939,917940,917941,917942,917943,917944,917945,917946,917947,917948,917949,917950,917951,917952,917953,917954,917955,917956,917957,917958,917959,917960,917961,917962,917963,917964,917965,917966,917967,917968,917969,917970,917971,917972,917973,917974,917975,917976,917977,917978,917979,917980,917981,917982,917983,917984,917985,917986,917987,917988,917989,917990,917991,917992,917993,917994,917995,917996,917997,917998,917999],"cs":[173,8203,12288],"de":[173,8203,12288],"es":[8203,12288],"fr":[173,8203,12288],"it":[160,173,12288],"ja":[173],"ko":[173,12288],"pl":[173,8203,12288],"pt-BR":[173,8203,12288],"qps-ploc":[160,173,8203,12288],"ru":[173,12288],"tr":[160,173,8203,12288],"zh-hans":[160,173,8203,12288],"zh-hant":[173,12288]}');
  }
  static getData() {
    return this._data || (this._data = new Set([...Object.values(Vr.getRawData())].flat())), this._data;
  }
  static isInvisibleCharacter(t) {
    return Vr.getData().has(t);
  }
  static get codePoints() {
    return Vr.getData();
  }
};
Vr._data = void 0;
let Fs = Vr;
const Ja = "default", d0 = "$initialize";
class m0 {
  constructor(t, n, r, s, i) {
    this.vsWorker = t, this.req = n, this.channel = r, this.method = s, this.args = i, this.type = 0;
  }
}
class nc {
  constructor(t, n, r, s) {
    this.vsWorker = t, this.seq = n, this.res = r, this.err = s, this.type = 1;
  }
}
class p0 {
  constructor(t, n, r, s, i) {
    this.vsWorker = t, this.req = n, this.channel = r, this.eventName = s, this.arg = i, this.type = 2;
  }
}
class g0 {
  constructor(t, n, r) {
    this.vsWorker = t, this.req = n, this.event = r, this.type = 3;
  }
}
class y0 {
  constructor(t, n) {
    this.vsWorker = t, this.req = n, this.type = 4;
  }
}
class b0 {
  constructor(t) {
    this._workerId = -1, this._handler = t, this._lastSentReq = 0, this._pendingReplies = /* @__PURE__ */ Object.create(null), this._pendingEmitters = /* @__PURE__ */ new Map(), this._pendingEvents = /* @__PURE__ */ new Map();
  }
  setWorkerId(t) {
    this._workerId = t;
  }
  sendMessage(t, n, r) {
    const s = String(++this._lastSentReq);
    return new Promise((i, a) => {
      this._pendingReplies[s] = {
        resolve: i,
        reject: a
      }, this._send(new m0(this._workerId, s, t, n, r));
    });
  }
  listen(t, n, r) {
    let s = null;
    const i = new Ht({
      onWillAddFirstListener: () => {
        s = String(++this._lastSentReq), this._pendingEmitters.set(s, i), this._send(new p0(this._workerId, s, t, n, r));
      },
      onDidRemoveLastListener: () => {
        this._pendingEmitters.delete(s), this._send(new y0(this._workerId, s)), s = null;
      }
    });
    return i.event;
  }
  handleMessage(t) {
    !t || !t.vsWorker || this._workerId !== -1 && t.vsWorker !== this._workerId || this._handleMessage(t);
  }
  createProxyToRemoteChannel(t, n) {
    const r = {
      get: (s, i) => (typeof i == "string" && !s[i] && (o1(i) ? s[i] = (a) => this.listen(t, i, a) : a1(i) ? s[i] = this.listen(t, i, void 0) : i.charCodeAt(0) === 36 && (s[i] = async (...a) => (await n?.(), this.sendMessage(t, i, a)))), s[i])
    };
    return new Proxy(/* @__PURE__ */ Object.create(null), r);
  }
  _handleMessage(t) {
    switch (t.type) {
      case 1:
        return this._handleReplyMessage(t);
      case 0:
        return this._handleRequestMessage(t);
      case 2:
        return this._handleSubscribeEventMessage(t);
      case 3:
        return this._handleEventMessage(t);
      case 4:
        return this._handleUnsubscribeEventMessage(t);
    }
  }
  _handleReplyMessage(t) {
    if (!this._pendingReplies[t.seq]) {
      console.warn("Got reply to unknown seq");
      return;
    }
    const n = this._pendingReplies[t.seq];
    if (delete this._pendingReplies[t.seq], t.err) {
      let r = t.err;
      t.err.$isError && (r = new Error(), r.name = t.err.name, r.message = t.err.message, r.stack = t.err.stack), n.reject(r);
      return;
    }
    n.resolve(t.res);
  }
  _handleRequestMessage(t) {
    const n = t.req;
    this._handler.handleMessage(t.channel, t.method, t.args).then((s) => {
      this._send(new nc(this._workerId, n, s, void 0));
    }, (s) => {
      s.detail instanceof Error && (s.detail = xo(s.detail)), this._send(new nc(this._workerId, n, void 0, xo(s)));
    });
  }
  _handleSubscribeEventMessage(t) {
    const n = t.req, r = this._handler.handleEvent(t.channel, t.eventName, t.arg)((s) => {
      this._send(new g0(this._workerId, n, s));
    });
    this._pendingEvents.set(n, r);
  }
  _handleEventMessage(t) {
    if (!this._pendingEmitters.has(t.req)) {
      console.warn("Got event for unknown req");
      return;
    }
    this._pendingEmitters.get(t.req).fire(t.event);
  }
  _handleUnsubscribeEventMessage(t) {
    if (!this._pendingEvents.has(t.req)) {
      console.warn("Got unsubscribe for unknown req");
      return;
    }
    this._pendingEvents.get(t.req).dispose(), this._pendingEvents.delete(t.req);
  }
  _send(t) {
    const n = [];
    if (t.type === 0)
      for (let r = 0; r < t.args.length; r++)
        t.args[r] instanceof ArrayBuffer && n.push(t.args[r]);
    else t.type === 1 && t.res instanceof ArrayBuffer && n.push(t.res);
    this._handler.sendMessage(t, n);
  }
}
function a1(e) {
  return e[0] === "o" && e[1] === "n" && i1(e.charCodeAt(2));
}
function o1(e) {
  return /^onDynamic/.test(e) && i1(e.charCodeAt(9));
}
class v0 {
  constructor(t, n) {
    this._localChannels = /* @__PURE__ */ new Map(), this._remoteChannels = /* @__PURE__ */ new Map(), this._protocol = new b0({
      sendMessage: (r, s) => {
        t(r, s);
      },
      handleMessage: (r, s, i) => this._handleMessage(r, s, i),
      handleEvent: (r, s, i) => this._handleEvent(r, s, i)
    }), this.requestHandler = n(this);
  }
  onmessage(t) {
    this._protocol.handleMessage(t);
  }
  _handleMessage(t, n, r) {
    if (t === Ja && n === d0)
      return this.initialize(r[0]);
    const s = t === Ja ? this.requestHandler : this._localChannels.get(t);
    if (!s)
      return Promise.reject(new Error(`Missing channel ${t} on worker thread`));
    if (typeof s[n] != "function")
      return Promise.reject(new Error(`Missing method ${n} on worker thread channel ${t}`));
    try {
      return Promise.resolve(s[n].apply(s, r));
    } catch (i) {
      return Promise.reject(i);
    }
  }
  _handleEvent(t, n, r) {
    const s = t === Ja ? this.requestHandler : this._localChannels.get(t);
    if (!s)
      throw new Error(`Missing channel ${t} on worker thread`);
    if (o1(n)) {
      const i = s[n].call(s, r);
      if (typeof i != "function")
        throw new Error(`Missing dynamic event ${n} on request handler.`);
      return i;
    }
    if (a1(n)) {
      const i = s[n];
      if (typeof i != "function")
        throw new Error(`Missing event ${n} on request handler.`);
      return i;
    }
    throw new Error(`Malformed event name ${n}`);
  }
  getChannel(t) {
    if (!this._remoteChannels.has(t)) {
      const n = this._protocol.createProxyToRemoteChannel(t);
      this._remoteChannels.set(t, n);
    }
    return this._remoteChannels.get(t);
  }
  async initialize(t) {
    this._protocol.setWorkerId(t);
  }
}
let rc = !1;
function w0(e) {
  if (rc)
    throw new Error("WebWorker already initialized!");
  rc = !0;
  const t = new v0((n) => globalThis.postMessage(n), (n) => e(n));
  return globalThis.onmessage = (n) => {
    t.onmessage(n.data);
  }, t;
}
class Nn {
  /**
   * Constructs a new DiffChange with the given sequence information
   * and content.
   */
  constructor(t, n, r, s) {
    this.originalStart = t, this.originalLength = n, this.modifiedStart = r, this.modifiedLength = s;
  }
  /**
   * The end point (exclusive) of the change in the original sequence.
   */
  getOriginalEnd() {
    return this.originalStart + this.originalLength;
  }
  /**
   * The end point (exclusive) of the change in the modified sequence.
   */
  getModifiedEnd() {
    return this.modifiedStart + this.modifiedLength;
  }
}
new To(() => new Uint8Array(256));
function sc(e, t) {
  return (t << 5) - t + e | 0;
}
function D0(e, t) {
  t = sc(149417, t);
  for (let n = 0, r = e.length; n < r; n++)
    t = sc(e.charCodeAt(n), t);
  return t;
}
class ic {
  constructor(t) {
    this.source = t;
  }
  getElements() {
    const t = this.source, n = new Int32Array(t.length);
    for (let r = 0, s = t.length; r < s; r++)
      n[r] = t.charCodeAt(r);
    return n;
  }
}
function S0(e, t, n) {
  return new Cn(new ic(e), new ic(t)).ComputeDiff(n).changes;
}
class vr {
  static Assert(t, n) {
    if (!t)
      throw new Error(n);
  }
}
class wr {
  /**
   * Copies a range of elements from an Array starting at the specified source index and pastes
   * them to another Array starting at the specified destination index. The length and the indexes
   * are specified as 64-bit integers.
   * sourceArray:
   *		The Array that contains the data to copy.
   * sourceIndex:
   *		A 64-bit integer that represents the index in the sourceArray at which copying begins.
   * destinationArray:
   *		The Array that receives the data.
   * destinationIndex:
   *		A 64-bit integer that represents the index in the destinationArray at which storing begins.
   * length:
   *		A 64-bit integer that represents the number of elements to copy.
   */
  static Copy(t, n, r, s, i) {
    for (let a = 0; a < i; a++)
      r[s + a] = t[n + a];
  }
  static Copy2(t, n, r, s, i) {
    for (let a = 0; a < i; a++)
      r[s + a] = t[n + a];
  }
}
class ac {
  /**
   * Constructs a new DiffChangeHelper for the given DiffSequences.
   */
  constructor() {
    this.m_changes = [], this.m_originalStart = 1073741824, this.m_modifiedStart = 1073741824, this.m_originalCount = 0, this.m_modifiedCount = 0;
  }
  /**
   * Marks the beginning of the next change in the set of differences.
   */
  MarkNextChange() {
    (this.m_originalCount > 0 || this.m_modifiedCount > 0) && this.m_changes.push(new Nn(this.m_originalStart, this.m_originalCount, this.m_modifiedStart, this.m_modifiedCount)), this.m_originalCount = 0, this.m_modifiedCount = 0, this.m_originalStart = 1073741824, this.m_modifiedStart = 1073741824;
  }
  /**
   * Adds the original element at the given position to the elements
   * affected by the current change. The modified index gives context
   * to the change position with respect to the original sequence.
   * @param originalIndex The index of the original element to add.
   * @param modifiedIndex The index of the modified element that provides corresponding position in the modified sequence.
   */
  AddOriginalElement(t, n) {
    this.m_originalStart = Math.min(this.m_originalStart, t), this.m_modifiedStart = Math.min(this.m_modifiedStart, n), this.m_originalCount++;
  }
  /**
   * Adds the modified element at the given position to the elements
   * affected by the current change. The original index gives context
   * to the change position with respect to the modified sequence.
   * @param originalIndex The index of the original element that provides corresponding position in the original sequence.
   * @param modifiedIndex The index of the modified element to add.
   */
  AddModifiedElement(t, n) {
    this.m_originalStart = Math.min(this.m_originalStart, t), this.m_modifiedStart = Math.min(this.m_modifiedStart, n), this.m_modifiedCount++;
  }
  /**
   * Retrieves all of the changes marked by the class.
   */
  getChanges() {
    return (this.m_originalCount > 0 || this.m_modifiedCount > 0) && this.MarkNextChange(), this.m_changes;
  }
  /**
   * Retrieves all of the changes marked by the class in the reverse order
   */
  getReverseChanges() {
    return (this.m_originalCount > 0 || this.m_modifiedCount > 0) && this.MarkNextChange(), this.m_changes.reverse(), this.m_changes;
  }
}
class Cn {
  /**
   * Constructs the DiffFinder
   */
  constructor(t, n, r = null) {
    this.ContinueProcessingPredicate = r, this._originalSequence = t, this._modifiedSequence = n;
    const [s, i, a] = Cn._getElements(t), [o, l, u] = Cn._getElements(n);
    this._hasStrings = a && u, this._originalStringElements = s, this._originalElementsOrHash = i, this._modifiedStringElements = o, this._modifiedElementsOrHash = l, this.m_forwardHistory = [], this.m_reverseHistory = [];
  }
  static _isStringArray(t) {
    return t.length > 0 && typeof t[0] == "string";
  }
  static _getElements(t) {
    const n = t.getElements();
    if (Cn._isStringArray(n)) {
      const r = new Int32Array(n.length);
      for (let s = 0, i = n.length; s < i; s++)
        r[s] = D0(n[s], 0);
      return [n, r, !0];
    }
    return n instanceof Int32Array ? [[], n, !1] : [[], new Int32Array(n), !1];
  }
  ElementsAreEqual(t, n) {
    return this._originalElementsOrHash[t] !== this._modifiedElementsOrHash[n] ? !1 : this._hasStrings ? this._originalStringElements[t] === this._modifiedStringElements[n] : !0;
  }
  ElementsAreStrictEqual(t, n) {
    if (!this.ElementsAreEqual(t, n))
      return !1;
    const r = Cn._getStrictElement(this._originalSequence, t), s = Cn._getStrictElement(this._modifiedSequence, n);
    return r === s;
  }
  static _getStrictElement(t, n) {
    return typeof t.getStrictElement == "function" ? t.getStrictElement(n) : null;
  }
  OriginalElementsAreEqual(t, n) {
    return this._originalElementsOrHash[t] !== this._originalElementsOrHash[n] ? !1 : this._hasStrings ? this._originalStringElements[t] === this._originalStringElements[n] : !0;
  }
  ModifiedElementsAreEqual(t, n) {
    return this._modifiedElementsOrHash[t] !== this._modifiedElementsOrHash[n] ? !1 : this._hasStrings ? this._modifiedStringElements[t] === this._modifiedStringElements[n] : !0;
  }
  ComputeDiff(t) {
    return this._ComputeDiff(0, this._originalElementsOrHash.length - 1, 0, this._modifiedElementsOrHash.length - 1, t);
  }
  /**
   * Computes the differences between the original and modified input
   * sequences on the bounded range.
   * @returns An array of the differences between the two input sequences.
   */
  _ComputeDiff(t, n, r, s, i) {
    const a = [!1];
    let o = this.ComputeDiffRecursive(t, n, r, s, a);
    return i && (o = this.PrettifyChanges(o)), {
      quitEarly: a[0],
      changes: o
    };
  }
  /**
   * Private helper method which computes the differences on the bounded range
   * recursively.
   * @returns An array of the differences between the two input sequences.
   */
  ComputeDiffRecursive(t, n, r, s, i) {
    for (i[0] = !1; t <= n && r <= s && this.ElementsAreEqual(t, r); )
      t++, r++;
    for (; n >= t && s >= r && this.ElementsAreEqual(n, s); )
      n--, s--;
    if (t > n || r > s) {
      let c;
      return r <= s ? (vr.Assert(t === n + 1, "originalStart should only be one more than originalEnd"), c = [
        new Nn(t, 0, r, s - r + 1)
      ]) : t <= n ? (vr.Assert(r === s + 1, "modifiedStart should only be one more than modifiedEnd"), c = [
        new Nn(t, n - t + 1, r, 0)
      ]) : (vr.Assert(t === n + 1, "originalStart should only be one more than originalEnd"), vr.Assert(r === s + 1, "modifiedStart should only be one more than modifiedEnd"), c = []), c;
    }
    const a = [0], o = [0], l = this.ComputeRecursionPoint(t, n, r, s, a, o, i), u = a[0], f = o[0];
    if (l !== null)
      return l;
    if (!i[0]) {
      const c = this.ComputeDiffRecursive(t, u, r, f, i);
      let d = [];
      return i[0] ? d = [
        new Nn(u + 1, n - (u + 1) + 1, f + 1, s - (f + 1) + 1)
      ] : d = this.ComputeDiffRecursive(u + 1, n, f + 1, s, i), this.ConcatenateChanges(c, d);
    }
    return [
      new Nn(t, n - t + 1, r, s - r + 1)
    ];
  }
  WALKTRACE(t, n, r, s, i, a, o, l, u, f, c, d, v, D, S, x, N, k) {
    let y = null, b = null, h = new ac(), m = n, p = r, E = v[0] - x[0] - s, w = -1073741824, L = this.m_forwardHistory.length - 1;
    do {
      const C = E + t;
      C === m || C < p && u[C - 1] < u[C + 1] ? (c = u[C + 1], D = c - E - s, c < w && h.MarkNextChange(), w = c, h.AddModifiedElement(c + 1, D), E = C + 1 - t) : (c = u[C - 1] + 1, D = c - E - s, c < w && h.MarkNextChange(), w = c - 1, h.AddOriginalElement(c, D + 1), E = C - 1 - t), L >= 0 && (u = this.m_forwardHistory[L], t = u[0], m = 1, p = u.length - 1);
    } while (--L >= -1);
    if (y = h.getReverseChanges(), k[0]) {
      let C = v[0] + 1, A = x[0] + 1;
      if (y !== null && y.length > 0) {
        const _ = y[y.length - 1];
        C = Math.max(C, _.getOriginalEnd()), A = Math.max(A, _.getModifiedEnd());
      }
      b = [
        new Nn(C, d - C + 1, A, S - A + 1)
      ];
    } else {
      h = new ac(), m = a, p = o, E = v[0] - x[0] - l, w = 1073741824, L = N ? this.m_reverseHistory.length - 1 : this.m_reverseHistory.length - 2;
      do {
        const C = E + i;
        C === m || C < p && f[C - 1] >= f[C + 1] ? (c = f[C + 1] - 1, D = c - E - l, c > w && h.MarkNextChange(), w = c + 1, h.AddOriginalElement(c + 1, D + 1), E = C + 1 - i) : (c = f[C - 1], D = c - E - l, c > w && h.MarkNextChange(), w = c, h.AddModifiedElement(c + 1, D + 1), E = C - 1 - i), L >= 0 && (f = this.m_reverseHistory[L], i = f[0], m = 1, p = f.length - 1);
      } while (--L >= -1);
      b = h.getChanges();
    }
    return this.ConcatenateChanges(y, b);
  }
  /**
   * Given the range to compute the diff on, this method finds the point:
   * (midOriginal, midModified)
   * that exists in the middle of the LCS of the two sequences and
   * is the point at which the LCS problem may be broken down recursively.
   * This method will try to keep the LCS trace in memory. If the LCS recursion
   * point is calculated and the full trace is available in memory, then this method
   * will return the change list.
   * @param originalStart The start bound of the original sequence range
   * @param originalEnd The end bound of the original sequence range
   * @param modifiedStart The start bound of the modified sequence range
   * @param modifiedEnd The end bound of the modified sequence range
   * @param midOriginal The middle point of the original sequence range
   * @param midModified The middle point of the modified sequence range
   * @returns The diff changes, if available, otherwise null
   */
  ComputeRecursionPoint(t, n, r, s, i, a, o) {
    let l = 0, u = 0, f = 0, c = 0, d = 0, v = 0;
    t--, r--, i[0] = 0, a[0] = 0, this.m_forwardHistory = [], this.m_reverseHistory = [];
    const D = n - t + (s - r), S = D + 1, x = new Int32Array(S), N = new Int32Array(S), k = s - r, y = n - t, b = t - r, h = n - s, p = (y - k) % 2 === 0;
    x[k] = t, N[y] = n, o[0] = !1;
    for (let E = 1; E <= D / 2 + 1; E++) {
      let w = 0, L = 0;
      f = this.ClipDiagonalBound(k - E, E, k, S), c = this.ClipDiagonalBound(k + E, E, k, S);
      for (let A = f; A <= c; A += 2) {
        A === f || A < c && x[A - 1] < x[A + 1] ? l = x[A + 1] : l = x[A - 1] + 1, u = l - (A - k) - b;
        const _ = l;
        for (; l < n && u < s && this.ElementsAreEqual(l + 1, u + 1); )
          l++, u++;
        if (x[A] = l, l + u > w + L && (w = l, L = u), !p && Math.abs(A - y) <= E - 1 && l >= N[A])
          return i[0] = l, a[0] = u, _ <= N[A] && E <= 1448 ? this.WALKTRACE(k, f, c, b, y, d, v, h, x, N, l, n, i, u, s, a, p, o) : null;
      }
      const C = (w - t + (L - r) - E) / 2;
      if (this.ContinueProcessingPredicate !== null && !this.ContinueProcessingPredicate(w, C))
        return o[0] = !0, i[0] = w, a[0] = L, C > 0 && E <= 1448 ? this.WALKTRACE(k, f, c, b, y, d, v, h, x, N, l, n, i, u, s, a, p, o) : (t++, r++, [
          new Nn(t, n - t + 1, r, s - r + 1)
        ]);
      d = this.ClipDiagonalBound(y - E, E, y, S), v = this.ClipDiagonalBound(y + E, E, y, S);
      for (let A = d; A <= v; A += 2) {
        A === d || A < v && N[A - 1] >= N[A + 1] ? l = N[A + 1] - 1 : l = N[A - 1], u = l - (A - y) - h;
        const _ = l;
        for (; l > t && u > r && this.ElementsAreEqual(l, u); )
          l--, u--;
        if (N[A] = l, p && Math.abs(A - k) <= E && l <= x[A])
          return i[0] = l, a[0] = u, _ >= x[A] && E <= 1448 ? this.WALKTRACE(k, f, c, b, y, d, v, h, x, N, l, n, i, u, s, a, p, o) : null;
      }
      if (E <= 1447) {
        let A = new Int32Array(c - f + 2);
        A[0] = k - f + 1, wr.Copy2(x, f, A, 1, c - f + 1), this.m_forwardHistory.push(A), A = new Int32Array(v - d + 2), A[0] = y - d + 1, wr.Copy2(N, d, A, 1, v - d + 1), this.m_reverseHistory.push(A);
      }
    }
    return this.WALKTRACE(k, f, c, b, y, d, v, h, x, N, l, n, i, u, s, a, p, o);
  }
  /**
   * Shifts the given changes to provide a more intuitive diff.
   * While the first element in a diff matches the first element after the diff,
   * we shift the diff down.
   *
   * @param changes The list of changes to shift
   * @returns The shifted changes
   */
  PrettifyChanges(t) {
    for (let n = 0; n < t.length; n++) {
      const r = t[n], s = n < t.length - 1 ? t[n + 1].originalStart : this._originalElementsOrHash.length, i = n < t.length - 1 ? t[n + 1].modifiedStart : this._modifiedElementsOrHash.length, a = r.originalLength > 0, o = r.modifiedLength > 0;
      for (; r.originalStart + r.originalLength < s && r.modifiedStart + r.modifiedLength < i && (!a || this.OriginalElementsAreEqual(r.originalStart, r.originalStart + r.originalLength)) && (!o || this.ModifiedElementsAreEqual(r.modifiedStart, r.modifiedStart + r.modifiedLength)); ) {
        const u = this.ElementsAreStrictEqual(r.originalStart, r.modifiedStart);
        if (this.ElementsAreStrictEqual(r.originalStart + r.originalLength, r.modifiedStart + r.modifiedLength) && !u)
          break;
        r.originalStart++, r.modifiedStart++;
      }
      const l = [null];
      if (n < t.length - 1 && this.ChangesOverlap(t[n], t[n + 1], l)) {
        t[n] = l[0], t.splice(n + 1, 1), n--;
        continue;
      }
    }
    for (let n = t.length - 1; n >= 0; n--) {
      const r = t[n];
      let s = 0, i = 0;
      if (n > 0) {
        const c = t[n - 1];
        s = c.originalStart + c.originalLength, i = c.modifiedStart + c.modifiedLength;
      }
      const a = r.originalLength > 0, o = r.modifiedLength > 0;
      let l = 0, u = this._boundaryScore(r.originalStart, r.originalLength, r.modifiedStart, r.modifiedLength);
      for (let c = 1; ; c++) {
        const d = r.originalStart - c, v = r.modifiedStart - c;
        if (d < s || v < i || a && !this.OriginalElementsAreEqual(d, d + r.originalLength) || o && !this.ModifiedElementsAreEqual(v, v + r.modifiedLength))
          break;
        const S = (d === s && v === i ? 5 : 0) + this._boundaryScore(d, r.originalLength, v, r.modifiedLength);
        S > u && (u = S, l = c);
      }
      r.originalStart -= l, r.modifiedStart -= l;
      const f = [null];
      if (n > 0 && this.ChangesOverlap(t[n - 1], t[n], f)) {
        t[n - 1] = f[0], t.splice(n, 1), n++;
        continue;
      }
    }
    if (this._hasStrings)
      for (let n = 1, r = t.length; n < r; n++) {
        const s = t[n - 1], i = t[n], a = i.originalStart - s.originalStart - s.originalLength, o = s.originalStart, l = i.originalStart + i.originalLength, u = l - o, f = s.modifiedStart, c = i.modifiedStart + i.modifiedLength, d = c - f;
        if (a < 5 && u < 20 && d < 20) {
          const v = this._findBetterContiguousSequence(o, u, f, d, a);
          if (v) {
            const [D, S] = v;
            (D !== s.originalStart + s.originalLength || S !== s.modifiedStart + s.modifiedLength) && (s.originalLength = D - s.originalStart, s.modifiedLength = S - s.modifiedStart, i.originalStart = D + a, i.modifiedStart = S + a, i.originalLength = l - i.originalStart, i.modifiedLength = c - i.modifiedStart);
          }
        }
      }
    return t;
  }
  _findBetterContiguousSequence(t, n, r, s, i) {
    if (n < i || s < i)
      return null;
    const a = t + n - i + 1, o = r + s - i + 1;
    let l = 0, u = 0, f = 0;
    for (let c = t; c < a; c++)
      for (let d = r; d < o; d++) {
        const v = this._contiguousSequenceScore(c, d, i);
        v > 0 && v > l && (l = v, u = c, f = d);
      }
    return l > 0 ? [u, f] : null;
  }
  _contiguousSequenceScore(t, n, r) {
    let s = 0;
    for (let i = 0; i < r; i++) {
      if (!this.ElementsAreEqual(t + i, n + i))
        return 0;
      s += this._originalStringElements[t + i].length;
    }
    return s;
  }
  _OriginalIsBoundary(t) {
    return t <= 0 || t >= this._originalElementsOrHash.length - 1 ? !0 : this._hasStrings && /^\s*$/.test(this._originalStringElements[t]);
  }
  _OriginalRegionIsBoundary(t, n) {
    if (this._OriginalIsBoundary(t) || this._OriginalIsBoundary(t - 1))
      return !0;
    if (n > 0) {
      const r = t + n;
      if (this._OriginalIsBoundary(r - 1) || this._OriginalIsBoundary(r))
        return !0;
    }
    return !1;
  }
  _ModifiedIsBoundary(t) {
    return t <= 0 || t >= this._modifiedElementsOrHash.length - 1 ? !0 : this._hasStrings && /^\s*$/.test(this._modifiedStringElements[t]);
  }
  _ModifiedRegionIsBoundary(t, n) {
    if (this._ModifiedIsBoundary(t) || this._ModifiedIsBoundary(t - 1))
      return !0;
    if (n > 0) {
      const r = t + n;
      if (this._ModifiedIsBoundary(r - 1) || this._ModifiedIsBoundary(r))
        return !0;
    }
    return !1;
  }
  _boundaryScore(t, n, r, s) {
    const i = this._OriginalRegionIsBoundary(t, n) ? 1 : 0, a = this._ModifiedRegionIsBoundary(r, s) ? 1 : 0;
    return i + a;
  }
  /**
   * Concatenates the two input DiffChange lists and returns the resulting
   * list.
   * @param The left changes
   * @param The right changes
   * @returns The concatenated list
   */
  ConcatenateChanges(t, n) {
    const r = [];
    if (t.length === 0 || n.length === 0)
      return n.length > 0 ? n : t;
    if (this.ChangesOverlap(t[t.length - 1], n[0], r)) {
      const s = new Array(t.length + n.length - 1);
      return wr.Copy(t, 0, s, 0, t.length - 1), s[t.length - 1] = r[0], wr.Copy(n, 1, s, t.length, n.length - 1), s;
    } else {
      const s = new Array(t.length + n.length);
      return wr.Copy(t, 0, s, 0, t.length), wr.Copy(n, 0, s, t.length, n.length), s;
    }
  }
  /**
   * Returns true if the two changes overlap and can be merged into a single
   * change
   * @param left The left change
   * @param right The right change
   * @param mergedChange The merged change if the two overlap, null otherwise
   * @returns True if the two changes overlap
   */
  ChangesOverlap(t, n, r) {
    if (vr.Assert(t.originalStart <= n.originalStart, "Left change is not less than or equal to right change"), vr.Assert(t.modifiedStart <= n.modifiedStart, "Left change is not less than or equal to right change"), t.originalStart + t.originalLength >= n.originalStart || t.modifiedStart + t.modifiedLength >= n.modifiedStart) {
      const s = t.originalStart;
      let i = t.originalLength;
      const a = t.modifiedStart;
      let o = t.modifiedLength;
      return t.originalStart + t.originalLength >= n.originalStart && (i = n.originalStart + n.originalLength - t.originalStart), t.modifiedStart + t.modifiedLength >= n.modifiedStart && (o = n.modifiedStart + n.modifiedLength - t.modifiedStart), r[0] = new Nn(s, i, a, o), !0;
    } else
      return r[0] = null, !1;
  }
  /**
   * Helper method used to clip a diagonal index to the range of valid
   * diagonals. This also decides whether or not the diagonal index,
   * if it exceeds the boundary, should be clipped to the boundary or clipped
   * one inside the boundary depending on the Even/Odd status of the boundary
   * and numDifferences.
   * @param diagonal The index of the diagonal to clip.
   * @param numDifferences The current number of differences being iterated upon.
   * @param diagonalBaseIndex The base reference diagonal.
   * @param numDiagonals The total number of diagonals.
   * @returns The clipped diagonal index.
   */
  ClipDiagonalBound(t, n, r, s) {
    if (t >= 0 && t < s)
      return t;
    const i = r, a = s - r - 1, o = n % 2 === 0;
    if (t < 0) {
      const l = i % 2 === 0;
      return o === l ? 0 : 1;
    } else {
      const l = a % 2 === 0;
      return o === l ? s - 1 : s - 2;
    }
  }
}
let Ne = class jn {
  constructor(t, n) {
    this.lineNumber = t, this.column = n;
  }
  /**
   * Create a new position from this position.
   *
   * @param newLineNumber new line number
   * @param newColumn new column
   */
  with(t = this.lineNumber, n = this.column) {
    return t === this.lineNumber && n === this.column ? this : new jn(t, n);
  }
  /**
   * Derive a new position from this position.
   *
   * @param deltaLineNumber line number delta
   * @param deltaColumn column delta
   */
  delta(t = 0, n = 0) {
    return this.with(Math.max(1, this.lineNumber + t), Math.max(1, this.column + n));
  }
  /**
   * Test if this position equals other position
   */
  equals(t) {
    return jn.equals(this, t);
  }
  /**
   * Test if position `a` equals position `b`
   */
  static equals(t, n) {
    return !t && !n ? !0 : !!t && !!n && t.lineNumber === n.lineNumber && t.column === n.column;
  }
  /**
   * Test if this position is before other position.
   * If the two positions are equal, the result will be false.
   */
  isBefore(t) {
    return jn.isBefore(this, t);
  }
  /**
   * Test if position `a` is before position `b`.
   * If the two positions are equal, the result will be false.
   */
  static isBefore(t, n) {
    return t.lineNumber < n.lineNumber ? !0 : n.lineNumber < t.lineNumber ? !1 : t.column < n.column;
  }
  /**
   * Test if this position is before other position.
   * If the two positions are equal, the result will be true.
   */
  isBeforeOrEqual(t) {
    return jn.isBeforeOrEqual(this, t);
  }
  /**
   * Test if position `a` is before position `b`.
   * If the two positions are equal, the result will be true.
   */
  static isBeforeOrEqual(t, n) {
    return t.lineNumber < n.lineNumber ? !0 : n.lineNumber < t.lineNumber ? !1 : t.column <= n.column;
  }
  /**
   * A function that compares positions, useful for sorting
   */
  static compare(t, n) {
    const r = t.lineNumber | 0, s = n.lineNumber | 0;
    if (r === s) {
      const i = t.column | 0, a = n.column | 0;
      return i - a;
    }
    return r - s;
  }
  /**
   * Clone this position.
   */
  clone() {
    return new jn(this.lineNumber, this.column);
  }
  /**
   * Convert to a human-readable representation.
   */
  toString() {
    return "(" + this.lineNumber + "," + this.column + ")";
  }
  // ---
  /**
   * Create a `Position` from an `IPosition`.
   */
  static lift(t) {
    return new jn(t.lineNumber, t.column);
  }
  /**
   * Test if `obj` is an `IPosition`.
   */
  static isIPosition(t) {
    return t && typeof t.lineNumber == "number" && typeof t.column == "number";
  }
  toJSON() {
    return {
      lineNumber: this.lineNumber,
      column: this.column
    };
  }
}, fe = class $e {
  constructor(t, n, r, s) {
    t > r || t === r && n > s ? (this.startLineNumber = r, this.startColumn = s, this.endLineNumber = t, this.endColumn = n) : (this.startLineNumber = t, this.startColumn = n, this.endLineNumber = r, this.endColumn = s);
  }
  /**
   * Test if this range is empty.
   */
  isEmpty() {
    return $e.isEmpty(this);
  }
  /**
   * Test if `range` is empty.
   */
  static isEmpty(t) {
    return t.startLineNumber === t.endLineNumber && t.startColumn === t.endColumn;
  }
  /**
   * Test if position is in this range. If the position is at the edges, will return true.
   */
  containsPosition(t) {
    return $e.containsPosition(this, t);
  }
  /**
   * Test if `position` is in `range`. If the position is at the edges, will return true.
   */
  static containsPosition(t, n) {
    return !(n.lineNumber < t.startLineNumber || n.lineNumber > t.endLineNumber || n.lineNumber === t.startLineNumber && n.column < t.startColumn || n.lineNumber === t.endLineNumber && n.column > t.endColumn);
  }
  /**
   * Test if `position` is in `range`. If the position is at the edges, will return false.
   * @internal
   */
  static strictContainsPosition(t, n) {
    return !(n.lineNumber < t.startLineNumber || n.lineNumber > t.endLineNumber || n.lineNumber === t.startLineNumber && n.column <= t.startColumn || n.lineNumber === t.endLineNumber && n.column >= t.endColumn);
  }
  /**
   * Test if range is in this range. If the range is equal to this range, will return true.
   */
  containsRange(t) {
    return $e.containsRange(this, t);
  }
  /**
   * Test if `otherRange` is in `range`. If the ranges are equal, will return true.
   */
  static containsRange(t, n) {
    return !(n.startLineNumber < t.startLineNumber || n.endLineNumber < t.startLineNumber || n.startLineNumber > t.endLineNumber || n.endLineNumber > t.endLineNumber || n.startLineNumber === t.startLineNumber && n.startColumn < t.startColumn || n.endLineNumber === t.endLineNumber && n.endColumn > t.endColumn);
  }
  /**
   * Test if `range` is strictly in this range. `range` must start after and end before this range for the result to be true.
   */
  strictContainsRange(t) {
    return $e.strictContainsRange(this, t);
  }
  /**
   * Test if `otherRange` is strictly in `range` (must start after, and end before). If the ranges are equal, will return false.
   */
  static strictContainsRange(t, n) {
    return !(n.startLineNumber < t.startLineNumber || n.endLineNumber < t.startLineNumber || n.startLineNumber > t.endLineNumber || n.endLineNumber > t.endLineNumber || n.startLineNumber === t.startLineNumber && n.startColumn <= t.startColumn || n.endLineNumber === t.endLineNumber && n.endColumn >= t.endColumn);
  }
  /**
   * A reunion of the two ranges.
   * The smallest position will be used as the start point, and the largest one as the end point.
   */
  plusRange(t) {
    return $e.plusRange(this, t);
  }
  /**
   * A reunion of the two ranges.
   * The smallest position will be used as the start point, and the largest one as the end point.
   */
  static plusRange(t, n) {
    let r, s, i, a;
    return n.startLineNumber < t.startLineNumber ? (r = n.startLineNumber, s = n.startColumn) : n.startLineNumber === t.startLineNumber ? (r = n.startLineNumber, s = Math.min(n.startColumn, t.startColumn)) : (r = t.startLineNumber, s = t.startColumn), n.endLineNumber > t.endLineNumber ? (i = n.endLineNumber, a = n.endColumn) : n.endLineNumber === t.endLineNumber ? (i = n.endLineNumber, a = Math.max(n.endColumn, t.endColumn)) : (i = t.endLineNumber, a = t.endColumn), new $e(r, s, i, a);
  }
  /**
   * A intersection of the two ranges.
   */
  intersectRanges(t) {
    return $e.intersectRanges(this, t);
  }
  /**
   * A intersection of the two ranges.
   */
  static intersectRanges(t, n) {
    let r = t.startLineNumber, s = t.startColumn, i = t.endLineNumber, a = t.endColumn;
    const o = n.startLineNumber, l = n.startColumn, u = n.endLineNumber, f = n.endColumn;
    return r < o ? (r = o, s = l) : r === o && (s = Math.max(s, l)), i > u ? (i = u, a = f) : i === u && (a = Math.min(a, f)), r > i || r === i && s > a ? null : new $e(r, s, i, a);
  }
  /**
   * Test if this range equals other.
   */
  equalsRange(t) {
    return $e.equalsRange(this, t);
  }
  /**
   * Test if range `a` equals `b`.
   */
  static equalsRange(t, n) {
    return !t && !n ? !0 : !!t && !!n && t.startLineNumber === n.startLineNumber && t.startColumn === n.startColumn && t.endLineNumber === n.endLineNumber && t.endColumn === n.endColumn;
  }
  /**
   * Return the end position (which will be after or equal to the start position)
   */
  getEndPosition() {
    return $e.getEndPosition(this);
  }
  /**
   * Return the end position (which will be after or equal to the start position)
   */
  static getEndPosition(t) {
    return new Ne(t.endLineNumber, t.endColumn);
  }
  /**
   * Return the start position (which will be before or equal to the end position)
   */
  getStartPosition() {
    return $e.getStartPosition(this);
  }
  /**
   * Return the start position (which will be before or equal to the end position)
   */
  static getStartPosition(t) {
    return new Ne(t.startLineNumber, t.startColumn);
  }
  /**
   * Transform to a user presentable string representation.
   */
  toString() {
    return "[" + this.startLineNumber + "," + this.startColumn + " -> " + this.endLineNumber + "," + this.endColumn + "]";
  }
  /**
   * Create a new range using this range's start position, and using endLineNumber and endColumn as the end position.
   */
  setEndPosition(t, n) {
    return new $e(this.startLineNumber, this.startColumn, t, n);
  }
  /**
   * Create a new range using this range's end position, and using startLineNumber and startColumn as the start position.
   */
  setStartPosition(t, n) {
    return new $e(t, n, this.endLineNumber, this.endColumn);
  }
  /**
   * Create a new empty range using this range's start position.
   */
  collapseToStart() {
    return $e.collapseToStart(this);
  }
  /**
   * Create a new empty range using this range's start position.
   */
  static collapseToStart(t) {
    return new $e(t.startLineNumber, t.startColumn, t.startLineNumber, t.startColumn);
  }
  /**
   * Create a new empty range using this range's end position.
   */
  collapseToEnd() {
    return $e.collapseToEnd(this);
  }
  /**
   * Create a new empty range using this range's end position.
   */
  static collapseToEnd(t) {
    return new $e(t.endLineNumber, t.endColumn, t.endLineNumber, t.endColumn);
  }
  /**
   * Moves the range by the given amount of lines.
   */
  delta(t) {
    return new $e(this.startLineNumber + t, this.startColumn, this.endLineNumber + t, this.endColumn);
  }
  isSingleLine() {
    return this.startLineNumber === this.endLineNumber;
  }
  // ---
  static fromPositions(t, n = t) {
    return new $e(t.lineNumber, t.column, n.lineNumber, n.column);
  }
  static lift(t) {
    return t ? new $e(t.startLineNumber, t.startColumn, t.endLineNumber, t.endColumn) : null;
  }
  /**
   * Test if `obj` is an `IRange`.
   */
  static isIRange(t) {
    return t && typeof t.startLineNumber == "number" && typeof t.startColumn == "number" && typeof t.endLineNumber == "number" && typeof t.endColumn == "number";
  }
  /**
   * Test if the two ranges are touching in any way.
   */
  static areIntersectingOrTouching(t, n) {
    return !(t.endLineNumber < n.startLineNumber || t.endLineNumber === n.startLineNumber && t.endColumn < n.startColumn || n.endLineNumber < t.startLineNumber || n.endLineNumber === t.startLineNumber && n.endColumn < t.startColumn);
  }
  /**
   * Test if the two ranges are intersecting. If the ranges are touching it returns true.
   */
  static areIntersecting(t, n) {
    return !(t.endLineNumber < n.startLineNumber || t.endLineNumber === n.startLineNumber && t.endColumn <= n.startColumn || n.endLineNumber < t.startLineNumber || n.endLineNumber === t.startLineNumber && n.endColumn <= t.startColumn);
  }
  /**
   * Test if the two ranges are intersecting, but not touching at all.
   */
  static areOnlyIntersecting(t, n) {
    return !(t.endLineNumber < n.startLineNumber - 1 || t.endLineNumber === n.startLineNumber && t.endColumn < n.startColumn - 1 || n.endLineNumber < t.startLineNumber - 1 || n.endLineNumber === t.startLineNumber && n.endColumn < t.startColumn - 1);
  }
  /**
   * A function that compares ranges, useful for sorting ranges
   * It will first compare ranges on the startPosition and then on the endPosition
   */
  static compareRangesUsingStarts(t, n) {
    if (t && n) {
      const i = t.startLineNumber | 0, a = n.startLineNumber | 0;
      if (i === a) {
        const o = t.startColumn | 0, l = n.startColumn | 0;
        if (o === l) {
          const u = t.endLineNumber | 0, f = n.endLineNumber | 0;
          if (u === f) {
            const c = t.endColumn | 0, d = n.endColumn | 0;
            return c - d;
          }
          return u - f;
        }
        return o - l;
      }
      return i - a;
    }
    return (t ? 1 : 0) - (n ? 1 : 0);
  }
  /**
   * A function that compares ranges, useful for sorting ranges
   * It will first compare ranges on the endPosition and then on the startPosition
   */
  static compareRangesUsingEnds(t, n) {
    return t.endLineNumber === n.endLineNumber ? t.endColumn === n.endColumn ? t.startLineNumber === n.startLineNumber ? t.startColumn - n.startColumn : t.startLineNumber - n.startLineNumber : t.endColumn - n.endColumn : t.endLineNumber - n.endLineNumber;
  }
  /**
   * Test if the range spans multiple lines.
   */
  static spansMultipleLines(t) {
    return t.endLineNumber > t.startLineNumber;
  }
  toJSON() {
    return this;
  }
};
function oc(e) {
  return e < 0 ? 0 : e > 255 ? 255 : e | 0;
}
function Dr(e) {
  return e < 0 ? 0 : e > 4294967295 ? 4294967295 : e | 0;
}
class nu {
  constructor(t) {
    const n = oc(t);
    this._defaultValue = n, this._asciiMap = nu._createAsciiMap(n), this._map = /* @__PURE__ */ new Map();
  }
  static _createAsciiMap(t) {
    const n = new Uint8Array(256);
    return n.fill(t), n;
  }
  set(t, n) {
    const r = oc(n);
    t >= 0 && t < 256 ? this._asciiMap[t] = r : this._map.set(t, r);
  }
  get(t) {
    return t >= 0 && t < 256 ? this._asciiMap[t] : this._map.get(t) || this._defaultValue;
  }
  clear() {
    this._asciiMap.fill(this._defaultValue), this._map.clear();
  }
}
class E0 {
  constructor(t, n, r) {
    const s = new Uint8Array(t * n);
    for (let i = 0, a = t * n; i < a; i++)
      s[i] = r;
    this._data = s, this.rows = t, this.cols = n;
  }
  get(t, n) {
    return this._data[t * this.cols + n];
  }
  set(t, n, r) {
    this._data[t * this.cols + n] = r;
  }
}
class A0 {
  constructor(t) {
    let n = 0, r = 0;
    for (let i = 0, a = t.length; i < a; i++) {
      const [o, l, u] = t[i];
      l > n && (n = l), o > r && (r = o), u > r && (r = u);
    }
    n++, r++;
    const s = new E0(
      r,
      n,
      0
      /* State.Invalid */
    );
    for (let i = 0, a = t.length; i < a; i++) {
      const [o, l, u] = t[i];
      s.set(o, l, u);
    }
    this._states = s, this._maxCharCode = n;
  }
  nextState(t, n) {
    return n < 0 || n >= this._maxCharCode ? 0 : this._states.get(t, n);
  }
}
let Qa = null;
function x0() {
  return Qa === null && (Qa = new A0([
    [
      1,
      104,
      2
      /* State.H */
    ],
    [
      1,
      72,
      2
      /* State.H */
    ],
    [
      1,
      102,
      6
      /* State.F */
    ],
    [
      1,
      70,
      6
      /* State.F */
    ],
    [
      2,
      116,
      3
      /* State.HT */
    ],
    [
      2,
      84,
      3
      /* State.HT */
    ],
    [
      3,
      116,
      4
      /* State.HTT */
    ],
    [
      3,
      84,
      4
      /* State.HTT */
    ],
    [
      4,
      112,
      5
      /* State.HTTP */
    ],
    [
      4,
      80,
      5
      /* State.HTTP */
    ],
    [
      5,
      115,
      9
      /* State.BeforeColon */
    ],
    [
      5,
      83,
      9
      /* State.BeforeColon */
    ],
    [
      5,
      58,
      10
      /* State.AfterColon */
    ],
    [
      6,
      105,
      7
      /* State.FI */
    ],
    [
      6,
      73,
      7
      /* State.FI */
    ],
    [
      7,
      108,
      8
      /* State.FIL */
    ],
    [
      7,
      76,
      8
      /* State.FIL */
    ],
    [
      8,
      101,
      9
      /* State.BeforeColon */
    ],
    [
      8,
      69,
      9
      /* State.BeforeColon */
    ],
    [
      9,
      58,
      10
      /* State.AfterColon */
    ],
    [
      10,
      47,
      11
      /* State.AlmostThere */
    ],
    [
      11,
      47,
      12
      /* State.End */
    ]
  ])), Qa;
}
let ys = null;
function N0() {
  if (ys === null) {
    ys = new nu(
      0
      /* CharacterClass.None */
    );
    const e = ` 	<>'"、。｡､，．：；‘〈「『〔（［｛｢｣｝］）〕』」〉’｀～…|`;
    for (let n = 0; n < e.length; n++)
      ys.set(
        e.charCodeAt(n),
        1
        /* CharacterClass.ForceTermination */
      );
    const t = ".,;:";
    for (let n = 0; n < t.length; n++)
      ys.set(
        t.charCodeAt(n),
        2
        /* CharacterClass.CannotEndIn */
      );
  }
  return ys;
}
class zi {
  static _createLink(t, n, r, s, i) {
    let a = i - 1;
    do {
      const o = n.charCodeAt(a);
      if (t.get(o) !== 2)
        break;
      a--;
    } while (a > s);
    if (s > 0) {
      const o = n.charCodeAt(s - 1), l = n.charCodeAt(a);
      (o === 40 && l === 41 || o === 91 && l === 93 || o === 123 && l === 125) && a--;
    }
    return {
      range: {
        startLineNumber: r,
        startColumn: s + 1,
        endLineNumber: r,
        endColumn: a + 2
      },
      url: n.substring(s, a + 1)
    };
  }
  static computeLinks(t, n = x0()) {
    const r = N0(), s = [];
    for (let i = 1, a = t.getLineCount(); i <= a; i++) {
      const o = t.getLineContent(i), l = o.length;
      let u = 0, f = 0, c = 0, d = 1, v = !1, D = !1, S = !1, x = !1;
      for (; u < l; ) {
        let N = !1;
        const k = o.charCodeAt(u);
        if (d === 13) {
          let y;
          switch (k) {
            case 40:
              v = !0, y = 0;
              break;
            case 41:
              y = v ? 0 : 1;
              break;
            case 91:
              S = !0, D = !0, y = 0;
              break;
            case 93:
              S = !1, y = D ? 0 : 1;
              break;
            case 123:
              x = !0, y = 0;
              break;
            case 125:
              y = x ? 0 : 1;
              break;
            // The following three rules make it that ' or " or ` are allowed inside links
            // only if the link is wrapped by some other quote character
            case 39:
            case 34:
            case 96:
              c === k ? y = 1 : c === 39 || c === 34 || c === 96 ? y = 0 : y = 1;
              break;
            case 42:
              y = c === 42 ? 1 : 0;
              break;
            case 32:
              y = S ? 0 : 1;
              break;
            default:
              y = r.get(k);
          }
          y === 1 && (s.push(zi._createLink(r, o, i, f, u)), N = !0);
        } else if (d === 12) {
          let y;
          k === 91 ? (D = !0, y = 0) : y = r.get(k), y === 1 ? N = !0 : d = 13;
        } else
          d = n.nextState(d, k), d === 0 && (N = !0);
        N && (d = 1, v = !1, D = !1, x = !1, f = u + 1, c = k), u++;
      }
      d === 13 && s.push(zi._createLink(r, o, i, f, l));
    }
    return s;
  }
}
function L0(e) {
  return !e || typeof e.getLineCount != "function" || typeof e.getLineContent != "function" ? [] : zi.computeLinks(e);
}
const Da = class Da {
  constructor() {
    this._defaultValueSet = [
      ["true", "false"],
      ["True", "False"],
      ["Private", "Public", "Friend", "ReadOnly", "Partial", "Protected", "WriteOnly"],
      ["public", "protected", "private"]
    ];
  }
  navigateValueSet(t, n, r, s, i) {
    if (t && n) {
      const a = this.doNavigateValueSet(n, i);
      if (a)
        return {
          range: t,
          value: a
        };
    }
    if (r && s) {
      const a = this.doNavigateValueSet(s, i);
      if (a)
        return {
          range: r,
          value: a
        };
    }
    return null;
  }
  doNavigateValueSet(t, n) {
    const r = this.numberReplace(t, n);
    return r !== null ? r : this.textReplace(t, n);
  }
  numberReplace(t, n) {
    const r = Math.pow(10, t.length - (t.lastIndexOf(".") + 1));
    let s = Number(t);
    const i = parseFloat(t);
    return !isNaN(s) && !isNaN(i) && s === i ? s === 0 && !n ? null : (s = Math.floor(s * r), s += n ? r : -r, String(s / r)) : null;
  }
  textReplace(t, n) {
    return this.valueSetsReplace(this._defaultValueSet, t, n);
  }
  valueSetsReplace(t, n, r) {
    let s = null;
    for (let i = 0, a = t.length; s === null && i < a; i++)
      s = this.valueSetReplace(t[i], n, r);
    return s;
  }
  valueSetReplace(t, n, r) {
    let s = t.indexOf(n);
    return s >= 0 ? (s += r ? 1 : -1, s < 0 ? s = t.length - 1 : s %= t.length, t[s]) : null;
  }
};
Da.INSTANCE = new Da();
let Oo = Da;
const l1 = Object.freeze(function(e, t) {
  const n = setTimeout(e.bind(t), 0);
  return { dispose() {
    clearTimeout(n);
  } };
});
var Gi;
(function(e) {
  function t(n) {
    return n === e.None || n === e.Cancelled || n instanceof Li ? !0 : !n || typeof n != "object" ? !1 : typeof n.isCancellationRequested == "boolean" && typeof n.onCancellationRequested == "function";
  }
  e.isCancellationToken = t, e.None = Object.freeze({
    isCancellationRequested: !1,
    onCancellationRequested: Lo.None
  }), e.Cancelled = Object.freeze({
    isCancellationRequested: !0,
    onCancellationRequested: l1
  });
})(Gi || (Gi = {}));
class Li {
  constructor() {
    this._isCancelled = !1, this._emitter = null;
  }
  cancel() {
    this._isCancelled || (this._isCancelled = !0, this._emitter && (this._emitter.fire(void 0), this.dispose()));
  }
  get isCancellationRequested() {
    return this._isCancelled;
  }
  get onCancellationRequested() {
    return this._isCancelled ? l1 : (this._emitter || (this._emitter = new Ht()), this._emitter.event);
  }
  dispose() {
    this._emitter && (this._emitter.dispose(), this._emitter = null);
  }
}
class k0 {
  constructor(t) {
    this._token = void 0, this._parentListener = void 0, this._parentListener = t && t.onCancellationRequested(this.cancel, this);
  }
  get token() {
    return this._token || (this._token = new Li()), this._token;
  }
  cancel() {
    this._token ? this._token instanceof Li && this._token.cancel() : this._token = Gi.Cancelled;
  }
  dispose(t = !1) {
    t && this.cancel(), this._parentListener?.dispose(), this._token ? this._token instanceof Li && this._token.dispose() : this._token = Gi.None;
  }
}
class ru {
  constructor() {
    this._keyCodeToStr = [], this._strToKeyCode = /* @__PURE__ */ Object.create(null);
  }
  define(t, n) {
    this._keyCodeToStr[t] = n, this._strToKeyCode[n.toLowerCase()] = t;
  }
  keyCodeToStr(t) {
    return this._keyCodeToStr[t];
  }
  strToKeyCode(t) {
    return this._strToKeyCode[t.toLowerCase()] || 0;
  }
}
const ki = new ru(), Ro = new ru(), Po = new ru(), C0 = new Array(230), F0 = /* @__PURE__ */ Object.create(null), _0 = /* @__PURE__ */ Object.create(null);
(function() {
  const t = [
    // immutable, scanCode, scanCodeStr, keyCode, keyCodeStr, eventKeyCode, vkey, usUserSettingsLabel, generalUserSettingsLabel
    [1, 0, "None", 0, "unknown", 0, "VK_UNKNOWN", "", ""],
    [1, 1, "Hyper", 0, "", 0, "", "", ""],
    [1, 2, "Super", 0, "", 0, "", "", ""],
    [1, 3, "Fn", 0, "", 0, "", "", ""],
    [1, 4, "FnLock", 0, "", 0, "", "", ""],
    [1, 5, "Suspend", 0, "", 0, "", "", ""],
    [1, 6, "Resume", 0, "", 0, "", "", ""],
    [1, 7, "Turbo", 0, "", 0, "", "", ""],
    [1, 8, "Sleep", 0, "", 0, "VK_SLEEP", "", ""],
    [1, 9, "WakeUp", 0, "", 0, "", "", ""],
    [0, 10, "KeyA", 31, "A", 65, "VK_A", "", ""],
    [0, 11, "KeyB", 32, "B", 66, "VK_B", "", ""],
    [0, 12, "KeyC", 33, "C", 67, "VK_C", "", ""],
    [0, 13, "KeyD", 34, "D", 68, "VK_D", "", ""],
    [0, 14, "KeyE", 35, "E", 69, "VK_E", "", ""],
    [0, 15, "KeyF", 36, "F", 70, "VK_F", "", ""],
    [0, 16, "KeyG", 37, "G", 71, "VK_G", "", ""],
    [0, 17, "KeyH", 38, "H", 72, "VK_H", "", ""],
    [0, 18, "KeyI", 39, "I", 73, "VK_I", "", ""],
    [0, 19, "KeyJ", 40, "J", 74, "VK_J", "", ""],
    [0, 20, "KeyK", 41, "K", 75, "VK_K", "", ""],
    [0, 21, "KeyL", 42, "L", 76, "VK_L", "", ""],
    [0, 22, "KeyM", 43, "M", 77, "VK_M", "", ""],
    [0, 23, "KeyN", 44, "N", 78, "VK_N", "", ""],
    [0, 24, "KeyO", 45, "O", 79, "VK_O", "", ""],
    [0, 25, "KeyP", 46, "P", 80, "VK_P", "", ""],
    [0, 26, "KeyQ", 47, "Q", 81, "VK_Q", "", ""],
    [0, 27, "KeyR", 48, "R", 82, "VK_R", "", ""],
    [0, 28, "KeyS", 49, "S", 83, "VK_S", "", ""],
    [0, 29, "KeyT", 50, "T", 84, "VK_T", "", ""],
    [0, 30, "KeyU", 51, "U", 85, "VK_U", "", ""],
    [0, 31, "KeyV", 52, "V", 86, "VK_V", "", ""],
    [0, 32, "KeyW", 53, "W", 87, "VK_W", "", ""],
    [0, 33, "KeyX", 54, "X", 88, "VK_X", "", ""],
    [0, 34, "KeyY", 55, "Y", 89, "VK_Y", "", ""],
    [0, 35, "KeyZ", 56, "Z", 90, "VK_Z", "", ""],
    [0, 36, "Digit1", 22, "1", 49, "VK_1", "", ""],
    [0, 37, "Digit2", 23, "2", 50, "VK_2", "", ""],
    [0, 38, "Digit3", 24, "3", 51, "VK_3", "", ""],
    [0, 39, "Digit4", 25, "4", 52, "VK_4", "", ""],
    [0, 40, "Digit5", 26, "5", 53, "VK_5", "", ""],
    [0, 41, "Digit6", 27, "6", 54, "VK_6", "", ""],
    [0, 42, "Digit7", 28, "7", 55, "VK_7", "", ""],
    [0, 43, "Digit8", 29, "8", 56, "VK_8", "", ""],
    [0, 44, "Digit9", 30, "9", 57, "VK_9", "", ""],
    [0, 45, "Digit0", 21, "0", 48, "VK_0", "", ""],
    [1, 46, "Enter", 3, "Enter", 13, "VK_RETURN", "", ""],
    [1, 47, "Escape", 9, "Escape", 27, "VK_ESCAPE", "", ""],
    [1, 48, "Backspace", 1, "Backspace", 8, "VK_BACK", "", ""],
    [1, 49, "Tab", 2, "Tab", 9, "VK_TAB", "", ""],
    [1, 50, "Space", 10, "Space", 32, "VK_SPACE", "", ""],
    [0, 51, "Minus", 88, "-", 189, "VK_OEM_MINUS", "-", "OEM_MINUS"],
    [0, 52, "Equal", 86, "=", 187, "VK_OEM_PLUS", "=", "OEM_PLUS"],
    [0, 53, "BracketLeft", 92, "[", 219, "VK_OEM_4", "[", "OEM_4"],
    [0, 54, "BracketRight", 94, "]", 221, "VK_OEM_6", "]", "OEM_6"],
    [0, 55, "Backslash", 93, "\\", 220, "VK_OEM_5", "\\", "OEM_5"],
    [0, 56, "IntlHash", 0, "", 0, "", "", ""],
    // has been dropped from the w3c spec
    [0, 57, "Semicolon", 85, ";", 186, "VK_OEM_1", ";", "OEM_1"],
    [0, 58, "Quote", 95, "'", 222, "VK_OEM_7", "'", "OEM_7"],
    [0, 59, "Backquote", 91, "`", 192, "VK_OEM_3", "`", "OEM_3"],
    [0, 60, "Comma", 87, ",", 188, "VK_OEM_COMMA", ",", "OEM_COMMA"],
    [0, 61, "Period", 89, ".", 190, "VK_OEM_PERIOD", ".", "OEM_PERIOD"],
    [0, 62, "Slash", 90, "/", 191, "VK_OEM_2", "/", "OEM_2"],
    [1, 63, "CapsLock", 8, "CapsLock", 20, "VK_CAPITAL", "", ""],
    [1, 64, "F1", 59, "F1", 112, "VK_F1", "", ""],
    [1, 65, "F2", 60, "F2", 113, "VK_F2", "", ""],
    [1, 66, "F3", 61, "F3", 114, "VK_F3", "", ""],
    [1, 67, "F4", 62, "F4", 115, "VK_F4", "", ""],
    [1, 68, "F5", 63, "F5", 116, "VK_F5", "", ""],
    [1, 69, "F6", 64, "F6", 117, "VK_F6", "", ""],
    [1, 70, "F7", 65, "F7", 118, "VK_F7", "", ""],
    [1, 71, "F8", 66, "F8", 119, "VK_F8", "", ""],
    [1, 72, "F9", 67, "F9", 120, "VK_F9", "", ""],
    [1, 73, "F10", 68, "F10", 121, "VK_F10", "", ""],
    [1, 74, "F11", 69, "F11", 122, "VK_F11", "", ""],
    [1, 75, "F12", 70, "F12", 123, "VK_F12", "", ""],
    [1, 76, "PrintScreen", 0, "", 0, "", "", ""],
    [1, 77, "ScrollLock", 84, "ScrollLock", 145, "VK_SCROLL", "", ""],
    [1, 78, "Pause", 7, "PauseBreak", 19, "VK_PAUSE", "", ""],
    [1, 79, "Insert", 19, "Insert", 45, "VK_INSERT", "", ""],
    [1, 80, "Home", 14, "Home", 36, "VK_HOME", "", ""],
    [1, 81, "PageUp", 11, "PageUp", 33, "VK_PRIOR", "", ""],
    [1, 82, "Delete", 20, "Delete", 46, "VK_DELETE", "", ""],
    [1, 83, "End", 13, "End", 35, "VK_END", "", ""],
    [1, 84, "PageDown", 12, "PageDown", 34, "VK_NEXT", "", ""],
    [1, 85, "ArrowRight", 17, "RightArrow", 39, "VK_RIGHT", "Right", ""],
    [1, 86, "ArrowLeft", 15, "LeftArrow", 37, "VK_LEFT", "Left", ""],
    [1, 87, "ArrowDown", 18, "DownArrow", 40, "VK_DOWN", "Down", ""],
    [1, 88, "ArrowUp", 16, "UpArrow", 38, "VK_UP", "Up", ""],
    [1, 89, "NumLock", 83, "NumLock", 144, "VK_NUMLOCK", "", ""],
    [1, 90, "NumpadDivide", 113, "NumPad_Divide", 111, "VK_DIVIDE", "", ""],
    [1, 91, "NumpadMultiply", 108, "NumPad_Multiply", 106, "VK_MULTIPLY", "", ""],
    [1, 92, "NumpadSubtract", 111, "NumPad_Subtract", 109, "VK_SUBTRACT", "", ""],
    [1, 93, "NumpadAdd", 109, "NumPad_Add", 107, "VK_ADD", "", ""],
    [1, 94, "NumpadEnter", 3, "", 0, "", "", ""],
    [1, 95, "Numpad1", 99, "NumPad1", 97, "VK_NUMPAD1", "", ""],
    [1, 96, "Numpad2", 100, "NumPad2", 98, "VK_NUMPAD2", "", ""],
    [1, 97, "Numpad3", 101, "NumPad3", 99, "VK_NUMPAD3", "", ""],
    [1, 98, "Numpad4", 102, "NumPad4", 100, "VK_NUMPAD4", "", ""],
    [1, 99, "Numpad5", 103, "NumPad5", 101, "VK_NUMPAD5", "", ""],
    [1, 100, "Numpad6", 104, "NumPad6", 102, "VK_NUMPAD6", "", ""],
    [1, 101, "Numpad7", 105, "NumPad7", 103, "VK_NUMPAD7", "", ""],
    [1, 102, "Numpad8", 106, "NumPad8", 104, "VK_NUMPAD8", "", ""],
    [1, 103, "Numpad9", 107, "NumPad9", 105, "VK_NUMPAD9", "", ""],
    [1, 104, "Numpad0", 98, "NumPad0", 96, "VK_NUMPAD0", "", ""],
    [1, 105, "NumpadDecimal", 112, "NumPad_Decimal", 110, "VK_DECIMAL", "", ""],
    [0, 106, "IntlBackslash", 97, "OEM_102", 226, "VK_OEM_102", "", ""],
    [1, 107, "ContextMenu", 58, "ContextMenu", 93, "", "", ""],
    [1, 108, "Power", 0, "", 0, "", "", ""],
    [1, 109, "NumpadEqual", 0, "", 0, "", "", ""],
    [1, 110, "F13", 71, "F13", 124, "VK_F13", "", ""],
    [1, 111, "F14", 72, "F14", 125, "VK_F14", "", ""],
    [1, 112, "F15", 73, "F15", 126, "VK_F15", "", ""],
    [1, 113, "F16", 74, "F16", 127, "VK_F16", "", ""],
    [1, 114, "F17", 75, "F17", 128, "VK_F17", "", ""],
    [1, 115, "F18", 76, "F18", 129, "VK_F18", "", ""],
    [1, 116, "F19", 77, "F19", 130, "VK_F19", "", ""],
    [1, 117, "F20", 78, "F20", 131, "VK_F20", "", ""],
    [1, 118, "F21", 79, "F21", 132, "VK_F21", "", ""],
    [1, 119, "F22", 80, "F22", 133, "VK_F22", "", ""],
    [1, 120, "F23", 81, "F23", 134, "VK_F23", "", ""],
    [1, 121, "F24", 82, "F24", 135, "VK_F24", "", ""],
    [1, 122, "Open", 0, "", 0, "", "", ""],
    [1, 123, "Help", 0, "", 0, "", "", ""],
    [1, 124, "Select", 0, "", 0, "", "", ""],
    [1, 125, "Again", 0, "", 0, "", "", ""],
    [1, 126, "Undo", 0, "", 0, "", "", ""],
    [1, 127, "Cut", 0, "", 0, "", "", ""],
    [1, 128, "Copy", 0, "", 0, "", "", ""],
    [1, 129, "Paste", 0, "", 0, "", "", ""],
    [1, 130, "Find", 0, "", 0, "", "", ""],
    [1, 131, "AudioVolumeMute", 117, "AudioVolumeMute", 173, "VK_VOLUME_MUTE", "", ""],
    [1, 132, "AudioVolumeUp", 118, "AudioVolumeUp", 175, "VK_VOLUME_UP", "", ""],
    [1, 133, "AudioVolumeDown", 119, "AudioVolumeDown", 174, "VK_VOLUME_DOWN", "", ""],
    [1, 134, "NumpadComma", 110, "NumPad_Separator", 108, "VK_SEPARATOR", "", ""],
    [0, 135, "IntlRo", 115, "ABNT_C1", 193, "VK_ABNT_C1", "", ""],
    [1, 136, "KanaMode", 0, "", 0, "", "", ""],
    [0, 137, "IntlYen", 0, "", 0, "", "", ""],
    [1, 138, "Convert", 0, "", 0, "", "", ""],
    [1, 139, "NonConvert", 0, "", 0, "", "", ""],
    [1, 140, "Lang1", 0, "", 0, "", "", ""],
    [1, 141, "Lang2", 0, "", 0, "", "", ""],
    [1, 142, "Lang3", 0, "", 0, "", "", ""],
    [1, 143, "Lang4", 0, "", 0, "", "", ""],
    [1, 144, "Lang5", 0, "", 0, "", "", ""],
    [1, 145, "Abort", 0, "", 0, "", "", ""],
    [1, 146, "Props", 0, "", 0, "", "", ""],
    [1, 147, "NumpadParenLeft", 0, "", 0, "", "", ""],
    [1, 148, "NumpadParenRight", 0, "", 0, "", "", ""],
    [1, 149, "NumpadBackspace", 0, "", 0, "", "", ""],
    [1, 150, "NumpadMemoryStore", 0, "", 0, "", "", ""],
    [1, 151, "NumpadMemoryRecall", 0, "", 0, "", "", ""],
    [1, 152, "NumpadMemoryClear", 0, "", 0, "", "", ""],
    [1, 153, "NumpadMemoryAdd", 0, "", 0, "", "", ""],
    [1, 154, "NumpadMemorySubtract", 0, "", 0, "", "", ""],
    [1, 155, "NumpadClear", 131, "Clear", 12, "VK_CLEAR", "", ""],
    [1, 156, "NumpadClearEntry", 0, "", 0, "", "", ""],
    [1, 0, "", 5, "Ctrl", 17, "VK_CONTROL", "", ""],
    [1, 0, "", 4, "Shift", 16, "VK_SHIFT", "", ""],
    [1, 0, "", 6, "Alt", 18, "VK_MENU", "", ""],
    [1, 0, "", 57, "Meta", 91, "VK_COMMAND", "", ""],
    [1, 157, "ControlLeft", 5, "", 0, "VK_LCONTROL", "", ""],
    [1, 158, "ShiftLeft", 4, "", 0, "VK_LSHIFT", "", ""],
    [1, 159, "AltLeft", 6, "", 0, "VK_LMENU", "", ""],
    [1, 160, "MetaLeft", 57, "", 0, "VK_LWIN", "", ""],
    [1, 161, "ControlRight", 5, "", 0, "VK_RCONTROL", "", ""],
    [1, 162, "ShiftRight", 4, "", 0, "VK_RSHIFT", "", ""],
    [1, 163, "AltRight", 6, "", 0, "VK_RMENU", "", ""],
    [1, 164, "MetaRight", 57, "", 0, "VK_RWIN", "", ""],
    [1, 165, "BrightnessUp", 0, "", 0, "", "", ""],
    [1, 166, "BrightnessDown", 0, "", 0, "", "", ""],
    [1, 167, "MediaPlay", 0, "", 0, "", "", ""],
    [1, 168, "MediaRecord", 0, "", 0, "", "", ""],
    [1, 169, "MediaFastForward", 0, "", 0, "", "", ""],
    [1, 170, "MediaRewind", 0, "", 0, "", "", ""],
    [1, 171, "MediaTrackNext", 124, "MediaTrackNext", 176, "VK_MEDIA_NEXT_TRACK", "", ""],
    [1, 172, "MediaTrackPrevious", 125, "MediaTrackPrevious", 177, "VK_MEDIA_PREV_TRACK", "", ""],
    [1, 173, "MediaStop", 126, "MediaStop", 178, "VK_MEDIA_STOP", "", ""],
    [1, 174, "Eject", 0, "", 0, "", "", ""],
    [1, 175, "MediaPlayPause", 127, "MediaPlayPause", 179, "VK_MEDIA_PLAY_PAUSE", "", ""],
    [1, 176, "MediaSelect", 128, "LaunchMediaPlayer", 181, "VK_MEDIA_LAUNCH_MEDIA_SELECT", "", ""],
    [1, 177, "LaunchMail", 129, "LaunchMail", 180, "VK_MEDIA_LAUNCH_MAIL", "", ""],
    [1, 178, "LaunchApp2", 130, "LaunchApp2", 183, "VK_MEDIA_LAUNCH_APP2", "", ""],
    [1, 179, "LaunchApp1", 0, "", 0, "VK_MEDIA_LAUNCH_APP1", "", ""],
    [1, 180, "SelectTask", 0, "", 0, "", "", ""],
    [1, 181, "LaunchScreenSaver", 0, "", 0, "", "", ""],
    [1, 182, "BrowserSearch", 120, "BrowserSearch", 170, "VK_BROWSER_SEARCH", "", ""],
    [1, 183, "BrowserHome", 121, "BrowserHome", 172, "VK_BROWSER_HOME", "", ""],
    [1, 184, "BrowserBack", 122, "BrowserBack", 166, "VK_BROWSER_BACK", "", ""],
    [1, 185, "BrowserForward", 123, "BrowserForward", 167, "VK_BROWSER_FORWARD", "", ""],
    [1, 186, "BrowserStop", 0, "", 0, "VK_BROWSER_STOP", "", ""],
    [1, 187, "BrowserRefresh", 0, "", 0, "VK_BROWSER_REFRESH", "", ""],
    [1, 188, "BrowserFavorites", 0, "", 0, "VK_BROWSER_FAVORITES", "", ""],
    [1, 189, "ZoomToggle", 0, "", 0, "", "", ""],
    [1, 190, "MailReply", 0, "", 0, "", "", ""],
    [1, 191, "MailForward", 0, "", 0, "", "", ""],
    [1, 192, "MailSend", 0, "", 0, "", "", ""],
    // See https://lists.w3.org/Archives/Public/www-dom/2010JulSep/att-0182/keyCode-spec.html
    // If an Input Method Editor is processing key input and the event is keydown, return 229.
    [1, 0, "", 114, "KeyInComposition", 229, "", "", ""],
    [1, 0, "", 116, "ABNT_C2", 194, "VK_ABNT_C2", "", ""],
    [1, 0, "", 96, "OEM_8", 223, "VK_OEM_8", "", ""],
    [1, 0, "", 0, "", 0, "VK_KANA", "", ""],
    [1, 0, "", 0, "", 0, "VK_HANGUL", "", ""],
    [1, 0, "", 0, "", 0, "VK_JUNJA", "", ""],
    [1, 0, "", 0, "", 0, "VK_FINAL", "", ""],
    [1, 0, "", 0, "", 0, "VK_HANJA", "", ""],
    [1, 0, "", 0, "", 0, "VK_KANJI", "", ""],
    [1, 0, "", 0, "", 0, "VK_CONVERT", "", ""],
    [1, 0, "", 0, "", 0, "VK_NONCONVERT", "", ""],
    [1, 0, "", 0, "", 0, "VK_ACCEPT", "", ""],
    [1, 0, "", 0, "", 0, "VK_MODECHANGE", "", ""],
    [1, 0, "", 0, "", 0, "VK_SELECT", "", ""],
    [1, 0, "", 0, "", 0, "VK_PRINT", "", ""],
    [1, 0, "", 0, "", 0, "VK_EXECUTE", "", ""],
    [1, 0, "", 0, "", 0, "VK_SNAPSHOT", "", ""],
    [1, 0, "", 0, "", 0, "VK_HELP", "", ""],
    [1, 0, "", 0, "", 0, "VK_APPS", "", ""],
    [1, 0, "", 0, "", 0, "VK_PROCESSKEY", "", ""],
    [1, 0, "", 0, "", 0, "VK_PACKET", "", ""],
    [1, 0, "", 0, "", 0, "VK_DBE_SBCSCHAR", "", ""],
    [1, 0, "", 0, "", 0, "VK_DBE_DBCSCHAR", "", ""],
    [1, 0, "", 0, "", 0, "VK_ATTN", "", ""],
    [1, 0, "", 0, "", 0, "VK_CRSEL", "", ""],
    [1, 0, "", 0, "", 0, "VK_EXSEL", "", ""],
    [1, 0, "", 0, "", 0, "VK_EREOF", "", ""],
    [1, 0, "", 0, "", 0, "VK_PLAY", "", ""],
    [1, 0, "", 0, "", 0, "VK_ZOOM", "", ""],
    [1, 0, "", 0, "", 0, "VK_NONAME", "", ""],
    [1, 0, "", 0, "", 0, "VK_PA1", "", ""],
    [1, 0, "", 0, "", 0, "VK_OEM_CLEAR", "", ""]
  ], n = [], r = [];
  for (const s of t) {
    const [i, a, o, l, u, f, c, d, v] = s;
    if (r[a] || (r[a] = !0, F0[o] = a, _0[o.toLowerCase()] = a), !n[l]) {
      if (n[l] = !0, !u)
        throw new Error(`String representation missing for key code ${l} around scan code ${o}`);
      ki.define(l, u), Ro.define(l, d || u), Po.define(l, v || d || u);
    }
    f && (C0[f] = l);
  }
})();
var lc;
(function(e) {
  function t(o) {
    return ki.keyCodeToStr(o);
  }
  e.toString = t;
  function n(o) {
    return ki.strToKeyCode(o);
  }
  e.fromString = n;
  function r(o) {
    return Ro.keyCodeToStr(o);
  }
  e.toUserSettingsUS = r;
  function s(o) {
    return Po.keyCodeToStr(o);
  }
  e.toUserSettingsGeneral = s;
  function i(o) {
    return Ro.strToKeyCode(o) || Po.strToKeyCode(o);
  }
  e.fromUserSettings = i;
  function a(o) {
    if (o >= 98 && o <= 113)
      return null;
    switch (o) {
      case 16:
        return "Up";
      case 18:
        return "Down";
      case 15:
        return "Left";
      case 17:
        return "Right";
    }
    return ki.keyCodeToStr(o);
  }
  e.toElectronAccelerator = a;
})(lc || (lc = {}));
function T0(e, t) {
  const n = (t & 65535) << 16 >>> 0;
  return (e | n) >>> 0;
}
let qr;
const Ka = globalThis.vscode;
if (typeof Ka < "u" && typeof Ka.process < "u") {
  const e = Ka.process;
  qr = {
    get platform() {
      return e.platform;
    },
    get arch() {
      return e.arch;
    },
    get env() {
      return e.env;
    },
    cwd() {
      return e.cwd();
    }
  };
} else typeof process < "u" && typeof process?.versions?.node == "string" ? qr = {
  get platform() {
    return process.platform;
  },
  get arch() {
    return process.arch;
  },
  get env() {
    return process.env;
  },
  cwd() {
    return process.env.VSCODE_CWD || process.cwd();
  }
} : qr = {
  // Supported
  get platform() {
    return Ys ? "win32" : Qg ? "darwin" : "linux";
  },
  get arch() {
  },
  // Unsupported
  get env() {
    return {};
  },
  cwd() {
    return "/";
  }
};
const Ji = qr.cwd, M0 = qr.env, O0 = qr.platform, R0 = 65, P0 = 97, I0 = 90, $0 = 122, tr = 46, We = 47, st = 92, tn = 58, B0 = 63;
class u1 extends Error {
  constructor(t, n, r) {
    let s;
    typeof n == "string" && n.indexOf("not ") === 0 ? (s = "must not be", n = n.replace(/^not /, "")) : s = "must be";
    const i = t.indexOf(".") !== -1 ? "property" : "argument";
    let a = `The "${t}" ${i} ${s} of type ${n}`;
    a += `. Received type ${typeof r}`, super(a), this.code = "ERR_INVALID_ARG_TYPE";
  }
}
function V0(e, t) {
  if (e === null || typeof e != "object")
    throw new u1(t, "Object", e);
}
function Re(e, t) {
  if (typeof e != "string")
    throw new u1(t, "string", e);
}
const In = O0 === "win32";
function ue(e) {
  return e === We || e === st;
}
function Io(e) {
  return e === We;
}
function nn(e) {
  return e >= R0 && e <= I0 || e >= P0 && e <= $0;
}
function Qi(e, t, n, r) {
  let s = "", i = 0, a = -1, o = 0, l = 0;
  for (let u = 0; u <= e.length; ++u) {
    if (u < e.length)
      l = e.charCodeAt(u);
    else {
      if (r(l))
        break;
      l = We;
    }
    if (r(l)) {
      if (!(a === u - 1 || o === 1)) if (o === 2) {
        if (s.length < 2 || i !== 2 || s.charCodeAt(s.length - 1) !== tr || s.charCodeAt(s.length - 2) !== tr) {
          if (s.length > 2) {
            const f = s.lastIndexOf(n);
            f === -1 ? (s = "", i = 0) : (s = s.slice(0, f), i = s.length - 1 - s.lastIndexOf(n)), a = u, o = 0;
            continue;
          } else if (s.length !== 0) {
            s = "", i = 0, a = u, o = 0;
            continue;
          }
        }
        t && (s += s.length > 0 ? `${n}..` : "..", i = 2);
      } else
        s.length > 0 ? s += `${n}${e.slice(a + 1, u)}` : s = e.slice(a + 1, u), i = u - a - 1;
      a = u, o = 0;
    } else l === tr && o !== -1 ? ++o : o = -1;
  }
  return s;
}
function j0(e) {
  return e ? `${e[0] === "." ? "" : "."}${e}` : "";
}
function c1(e, t) {
  V0(t, "pathObject");
  const n = t.dir || t.root, r = t.base || `${t.name || ""}${j0(t.ext)}`;
  return n ? n === t.root ? `${n}${r}` : `${n}${e}${r}` : r;
}
const et = {
  // path.resolve([from ...], to)
  resolve(...e) {
    let t = "", n = "", r = !1;
    for (let s = e.length - 1; s >= -1; s--) {
      let i;
      if (s >= 0) {
        if (i = e[s], Re(i, `paths[${s}]`), i.length === 0)
          continue;
      } else t.length === 0 ? i = Ji() : (i = M0[`=${t}`] || Ji(), (i === void 0 || i.slice(0, 2).toLowerCase() !== t.toLowerCase() && i.charCodeAt(2) === st) && (i = `${t}\\`));
      const a = i.length;
      let o = 0, l = "", u = !1;
      const f = i.charCodeAt(0);
      if (a === 1)
        ue(f) && (o = 1, u = !0);
      else if (ue(f))
        if (u = !0, ue(i.charCodeAt(1))) {
          let c = 2, d = c;
          for (; c < a && !ue(i.charCodeAt(c)); )
            c++;
          if (c < a && c !== d) {
            const v = i.slice(d, c);
            for (d = c; c < a && ue(i.charCodeAt(c)); )
              c++;
            if (c < a && c !== d) {
              for (d = c; c < a && !ue(i.charCodeAt(c)); )
                c++;
              (c === a || c !== d) && (l = `\\\\${v}\\${i.slice(d, c)}`, o = c);
            }
          }
        } else
          o = 1;
      else nn(f) && i.charCodeAt(1) === tn && (l = i.slice(0, 2), o = 2, a > 2 && ue(i.charCodeAt(2)) && (u = !0, o = 3));
      if (l.length > 0)
        if (t.length > 0) {
          if (l.toLowerCase() !== t.toLowerCase())
            continue;
        } else
          t = l;
      if (r) {
        if (t.length > 0)
          break;
      } else if (n = `${i.slice(o)}\\${n}`, r = u, u && t.length > 0)
        break;
    }
    return n = Qi(n, !r, "\\", ue), r ? `${t}\\${n}` : `${t}${n}` || ".";
  },
  normalize(e) {
    Re(e, "path");
    const t = e.length;
    if (t === 0)
      return ".";
    let n = 0, r, s = !1;
    const i = e.charCodeAt(0);
    if (t === 1)
      return Io(i) ? "\\" : e;
    if (ue(i))
      if (s = !0, ue(e.charCodeAt(1))) {
        let o = 2, l = o;
        for (; o < t && !ue(e.charCodeAt(o)); )
          o++;
        if (o < t && o !== l) {
          const u = e.slice(l, o);
          for (l = o; o < t && ue(e.charCodeAt(o)); )
            o++;
          if (o < t && o !== l) {
            for (l = o; o < t && !ue(e.charCodeAt(o)); )
              o++;
            if (o === t)
              return `\\\\${u}\\${e.slice(l)}\\`;
            o !== l && (r = `\\\\${u}\\${e.slice(l, o)}`, n = o);
          }
        }
      } else
        n = 1;
    else nn(i) && e.charCodeAt(1) === tn && (r = e.slice(0, 2), n = 2, t > 2 && ue(e.charCodeAt(2)) && (s = !0, n = 3));
    let a = n < t ? Qi(e.slice(n), !s, "\\", ue) : "";
    if (a.length === 0 && !s && (a = "."), a.length > 0 && ue(e.charCodeAt(t - 1)) && (a += "\\"), !s && r === void 0 && e.includes(":")) {
      if (a.length >= 2 && nn(a.charCodeAt(0)) && a.charCodeAt(1) === tn)
        return `.\\${a}`;
      let o = e.indexOf(":");
      do
        if (o === t - 1 || ue(e.charCodeAt(o + 1)))
          return `.\\${a}`;
      while ((o = e.indexOf(":", o + 1)) !== -1);
    }
    return r === void 0 ? s ? `\\${a}` : a : s ? `${r}\\${a}` : `${r}${a}`;
  },
  isAbsolute(e) {
    Re(e, "path");
    const t = e.length;
    if (t === 0)
      return !1;
    const n = e.charCodeAt(0);
    return ue(n) || // Possible device root
    t > 2 && nn(n) && e.charCodeAt(1) === tn && ue(e.charCodeAt(2));
  },
  join(...e) {
    if (e.length === 0)
      return ".";
    let t, n;
    for (let i = 0; i < e.length; ++i) {
      const a = e[i];
      Re(a, "path"), a.length > 0 && (t === void 0 ? t = n = a : t += `\\${a}`);
    }
    if (t === void 0)
      return ".";
    let r = !0, s = 0;
    if (typeof n == "string" && ue(n.charCodeAt(0))) {
      ++s;
      const i = n.length;
      i > 1 && ue(n.charCodeAt(1)) && (++s, i > 2 && (ue(n.charCodeAt(2)) ? ++s : r = !1));
    }
    if (r) {
      for (; s < t.length && ue(t.charCodeAt(s)); )
        s++;
      s >= 2 && (t = `\\${t.slice(s)}`);
    }
    return et.normalize(t);
  },
  // It will solve the relative path from `from` to `to`, for instance:
  //  from = 'C:\\orandea\\test\\aaa'
  //  to = 'C:\\orandea\\impl\\bbb'
  // The output of the function should be: '..\\..\\impl\\bbb'
  relative(e, t) {
    if (Re(e, "from"), Re(t, "to"), e === t)
      return "";
    const n = et.resolve(e), r = et.resolve(t);
    if (n === r || (e = n.toLowerCase(), t = r.toLowerCase(), e === t))
      return "";
    if (n.length !== e.length || r.length !== t.length) {
      const D = n.split("\\"), S = r.split("\\");
      D[D.length - 1] === "" && D.pop(), S[S.length - 1] === "" && S.pop();
      const x = D.length, N = S.length, k = x < N ? x : N;
      let y;
      for (y = 0; y < k && D[y].toLowerCase() === S[y].toLowerCase(); y++)
        ;
      return y === 0 ? r : y === k ? N > k ? S.slice(y).join("\\") : x > k ? "..\\".repeat(x - 1 - y) + ".." : "" : "..\\".repeat(x - y) + S.slice(y).join("\\");
    }
    let s = 0;
    for (; s < e.length && e.charCodeAt(s) === st; )
      s++;
    let i = e.length;
    for (; i - 1 > s && e.charCodeAt(i - 1) === st; )
      i--;
    const a = i - s;
    let o = 0;
    for (; o < t.length && t.charCodeAt(o) === st; )
      o++;
    let l = t.length;
    for (; l - 1 > o && t.charCodeAt(l - 1) === st; )
      l--;
    const u = l - o, f = a < u ? a : u;
    let c = -1, d = 0;
    for (; d < f; d++) {
      const D = e.charCodeAt(s + d);
      if (D !== t.charCodeAt(o + d))
        break;
      D === st && (c = d);
    }
    if (d !== f) {
      if (c === -1)
        return r;
    } else {
      if (u > f) {
        if (t.charCodeAt(o + d) === st)
          return r.slice(o + d + 1);
        if (d === 2)
          return r.slice(o + d);
      }
      a > f && (e.charCodeAt(s + d) === st ? c = d : d === 2 && (c = 3)), c === -1 && (c = 0);
    }
    let v = "";
    for (d = s + c + 1; d <= i; ++d)
      (d === i || e.charCodeAt(d) === st) && (v += v.length === 0 ? ".." : "\\..");
    return o += c, v.length > 0 ? `${v}${r.slice(o, l)}` : (r.charCodeAt(o) === st && ++o, r.slice(o, l));
  },
  toNamespacedPath(e) {
    if (typeof e != "string" || e.length === 0)
      return e;
    const t = et.resolve(e);
    if (t.length <= 2)
      return e;
    if (t.charCodeAt(0) === st) {
      if (t.charCodeAt(1) === st) {
        const n = t.charCodeAt(2);
        if (n !== B0 && n !== tr)
          return `\\\\?\\UNC\\${t.slice(2)}`;
      }
    } else if (nn(t.charCodeAt(0)) && t.charCodeAt(1) === tn && t.charCodeAt(2) === st)
      return `\\\\?\\${t}`;
    return t;
  },
  dirname(e) {
    Re(e, "path");
    const t = e.length;
    if (t === 0)
      return ".";
    let n = -1, r = 0;
    const s = e.charCodeAt(0);
    if (t === 1)
      return ue(s) ? e : ".";
    if (ue(s)) {
      if (n = r = 1, ue(e.charCodeAt(1))) {
        let o = 2, l = o;
        for (; o < t && !ue(e.charCodeAt(o)); )
          o++;
        if (o < t && o !== l) {
          for (l = o; o < t && ue(e.charCodeAt(o)); )
            o++;
          if (o < t && o !== l) {
            for (l = o; o < t && !ue(e.charCodeAt(o)); )
              o++;
            if (o === t)
              return e;
            o !== l && (n = r = o + 1);
          }
        }
      }
    } else nn(s) && e.charCodeAt(1) === tn && (n = t > 2 && ue(e.charCodeAt(2)) ? 3 : 2, r = n);
    let i = -1, a = !0;
    for (let o = t - 1; o >= r; --o)
      if (ue(e.charCodeAt(o))) {
        if (!a) {
          i = o;
          break;
        }
      } else
        a = !1;
    if (i === -1) {
      if (n === -1)
        return ".";
      i = n;
    }
    return e.slice(0, i);
  },
  basename(e, t) {
    t !== void 0 && Re(t, "suffix"), Re(e, "path");
    let n = 0, r = -1, s = !0, i;
    if (e.length >= 2 && nn(e.charCodeAt(0)) && e.charCodeAt(1) === tn && (n = 2), t !== void 0 && t.length > 0 && t.length <= e.length) {
      if (t === e)
        return "";
      let a = t.length - 1, o = -1;
      for (i = e.length - 1; i >= n; --i) {
        const l = e.charCodeAt(i);
        if (ue(l)) {
          if (!s) {
            n = i + 1;
            break;
          }
        } else
          o === -1 && (s = !1, o = i + 1), a >= 0 && (l === t.charCodeAt(a) ? --a === -1 && (r = i) : (a = -1, r = o));
      }
      return n === r ? r = o : r === -1 && (r = e.length), e.slice(n, r);
    }
    for (i = e.length - 1; i >= n; --i)
      if (ue(e.charCodeAt(i))) {
        if (!s) {
          n = i + 1;
          break;
        }
      } else r === -1 && (s = !1, r = i + 1);
    return r === -1 ? "" : e.slice(n, r);
  },
  extname(e) {
    Re(e, "path");
    let t = 0, n = -1, r = 0, s = -1, i = !0, a = 0;
    e.length >= 2 && e.charCodeAt(1) === tn && nn(e.charCodeAt(0)) && (t = r = 2);
    for (let o = e.length - 1; o >= t; --o) {
      const l = e.charCodeAt(o);
      if (ue(l)) {
        if (!i) {
          r = o + 1;
          break;
        }
        continue;
      }
      s === -1 && (i = !1, s = o + 1), l === tr ? n === -1 ? n = o : a !== 1 && (a = 1) : n !== -1 && (a = -1);
    }
    return n === -1 || s === -1 || // We saw a non-dot character immediately before the dot
    a === 0 || // The (right-most) trimmed path component is exactly '..'
    a === 1 && n === s - 1 && n === r + 1 ? "" : e.slice(n, s);
  },
  format: c1.bind(null, "\\"),
  parse(e) {
    Re(e, "path");
    const t = { root: "", dir: "", base: "", ext: "", name: "" };
    if (e.length === 0)
      return t;
    const n = e.length;
    let r = 0, s = e.charCodeAt(0);
    if (n === 1)
      return ue(s) ? (t.root = t.dir = e, t) : (t.base = t.name = e, t);
    if (ue(s)) {
      if (r = 1, ue(e.charCodeAt(1))) {
        let c = 2, d = c;
        for (; c < n && !ue(e.charCodeAt(c)); )
          c++;
        if (c < n && c !== d) {
          for (d = c; c < n && ue(e.charCodeAt(c)); )
            c++;
          if (c < n && c !== d) {
            for (d = c; c < n && !ue(e.charCodeAt(c)); )
              c++;
            c === n ? r = c : c !== d && (r = c + 1);
          }
        }
      }
    } else if (nn(s) && e.charCodeAt(1) === tn) {
      if (n <= 2)
        return t.root = t.dir = e, t;
      if (r = 2, ue(e.charCodeAt(2))) {
        if (n === 3)
          return t.root = t.dir = e, t;
        r = 3;
      }
    }
    r > 0 && (t.root = e.slice(0, r));
    let i = -1, a = r, o = -1, l = !0, u = e.length - 1, f = 0;
    for (; u >= r; --u) {
      if (s = e.charCodeAt(u), ue(s)) {
        if (!l) {
          a = u + 1;
          break;
        }
        continue;
      }
      o === -1 && (l = !1, o = u + 1), s === tr ? i === -1 ? i = u : f !== 1 && (f = 1) : i !== -1 && (f = -1);
    }
    return o !== -1 && (i === -1 || // We saw a non-dot character immediately before the dot
    f === 0 || // The (right-most) trimmed path component is exactly '..'
    f === 1 && i === o - 1 && i === a + 1 ? t.base = t.name = e.slice(a, o) : (t.name = e.slice(a, i), t.base = e.slice(a, o), t.ext = e.slice(i, o))), a > 0 && a !== r ? t.dir = e.slice(0, a - 1) : t.dir = t.root, t;
  },
  sep: "\\",
  delimiter: ";",
  win32: null,
  posix: null
}, U0 = (() => {
  if (In) {
    const e = /\\/g;
    return () => {
      const t = Ji().replace(e, "/");
      return t.slice(t.indexOf("/"));
    };
  }
  return () => Ji();
})(), ft = {
  // path.resolve([from ...], to)
  resolve(...e) {
    let t = "", n = !1;
    for (let r = e.length - 1; r >= 0 && !n; r--) {
      const s = e[r];
      Re(s, `paths[${r}]`), s.length !== 0 && (t = `${s}/${t}`, n = s.charCodeAt(0) === We);
    }
    if (!n) {
      const r = U0();
      t = `${r}/${t}`, n = r.charCodeAt(0) === We;
    }
    return t = Qi(t, !n, "/", Io), n ? `/${t}` : t.length > 0 ? t : ".";
  },
  normalize(e) {
    if (Re(e, "path"), e.length === 0)
      return ".";
    const t = e.charCodeAt(0) === We, n = e.charCodeAt(e.length - 1) === We;
    return e = Qi(e, !t, "/", Io), e.length === 0 ? t ? "/" : n ? "./" : "." : (n && (e += "/"), t ? `/${e}` : e);
  },
  isAbsolute(e) {
    return Re(e, "path"), e.length > 0 && e.charCodeAt(0) === We;
  },
  join(...e) {
    if (e.length === 0)
      return ".";
    const t = [];
    for (let n = 0; n < e.length; ++n) {
      const r = e[n];
      Re(r, "path"), r.length > 0 && t.push(r);
    }
    return t.length === 0 ? "." : ft.normalize(t.join("/"));
  },
  relative(e, t) {
    if (Re(e, "from"), Re(t, "to"), e === t || (e = ft.resolve(e), t = ft.resolve(t), e === t))
      return "";
    const n = 1, r = e.length, s = r - n, i = 1, a = t.length - i, o = s < a ? s : a;
    let l = -1, u = 0;
    for (; u < o; u++) {
      const c = e.charCodeAt(n + u);
      if (c !== t.charCodeAt(i + u))
        break;
      c === We && (l = u);
    }
    if (u === o)
      if (a > o) {
        if (t.charCodeAt(i + u) === We)
          return t.slice(i + u + 1);
        if (u === 0)
          return t.slice(i + u);
      } else s > o && (e.charCodeAt(n + u) === We ? l = u : u === 0 && (l = 0));
    let f = "";
    for (u = n + l + 1; u <= r; ++u)
      (u === r || e.charCodeAt(u) === We) && (f += f.length === 0 ? ".." : "/..");
    return `${f}${t.slice(i + l)}`;
  },
  toNamespacedPath(e) {
    return e;
  },
  dirname(e) {
    if (Re(e, "path"), e.length === 0)
      return ".";
    const t = e.charCodeAt(0) === We;
    let n = -1, r = !0;
    for (let s = e.length - 1; s >= 1; --s)
      if (e.charCodeAt(s) === We) {
        if (!r) {
          n = s;
          break;
        }
      } else
        r = !1;
    return n === -1 ? t ? "/" : "." : t && n === 1 ? "//" : e.slice(0, n);
  },
  basename(e, t) {
    t !== void 0 && Re(t, "suffix"), Re(e, "path");
    let n = 0, r = -1, s = !0, i;
    if (t !== void 0 && t.length > 0 && t.length <= e.length) {
      if (t === e)
        return "";
      let a = t.length - 1, o = -1;
      for (i = e.length - 1; i >= 0; --i) {
        const l = e.charCodeAt(i);
        if (l === We) {
          if (!s) {
            n = i + 1;
            break;
          }
        } else
          o === -1 && (s = !1, o = i + 1), a >= 0 && (l === t.charCodeAt(a) ? --a === -1 && (r = i) : (a = -1, r = o));
      }
      return n === r ? r = o : r === -1 && (r = e.length), e.slice(n, r);
    }
    for (i = e.length - 1; i >= 0; --i)
      if (e.charCodeAt(i) === We) {
        if (!s) {
          n = i + 1;
          break;
        }
      } else r === -1 && (s = !1, r = i + 1);
    return r === -1 ? "" : e.slice(n, r);
  },
  extname(e) {
    Re(e, "path");
    let t = -1, n = 0, r = -1, s = !0, i = 0;
    for (let a = e.length - 1; a >= 0; --a) {
      const o = e[a];
      if (o === "/") {
        if (!s) {
          n = a + 1;
          break;
        }
        continue;
      }
      r === -1 && (s = !1, r = a + 1), o === "." ? t === -1 ? t = a : i !== 1 && (i = 1) : t !== -1 && (i = -1);
    }
    return t === -1 || r === -1 || // We saw a non-dot character immediately before the dot
    i === 0 || // The (right-most) trimmed path component is exactly '..'
    i === 1 && t === r - 1 && t === n + 1 ? "" : e.slice(t, r);
  },
  format: c1.bind(null, "/"),
  parse(e) {
    Re(e, "path");
    const t = { root: "", dir: "", base: "", ext: "", name: "" };
    if (e.length === 0)
      return t;
    const n = e.charCodeAt(0) === We;
    let r;
    n ? (t.root = "/", r = 1) : r = 0;
    let s = -1, i = 0, a = -1, o = !0, l = e.length - 1, u = 0;
    for (; l >= r; --l) {
      const f = e.charCodeAt(l);
      if (f === We) {
        if (!o) {
          i = l + 1;
          break;
        }
        continue;
      }
      a === -1 && (o = !1, a = l + 1), f === tr ? s === -1 ? s = l : u !== 1 && (u = 1) : s !== -1 && (u = -1);
    }
    if (a !== -1) {
      const f = i === 0 && n ? 1 : i;
      s === -1 || // We saw a non-dot character immediately before the dot
      u === 0 || // The (right-most) trimmed path component is exactly '..'
      u === 1 && s === a - 1 && s === i + 1 ? t.base = t.name = e.slice(f, a) : (t.name = e.slice(f, s), t.base = e.slice(f, a), t.ext = e.slice(s, a));
    }
    return i > 0 ? t.dir = e.slice(0, i - 1) : n && (t.dir = "/"), t;
  },
  sep: "/",
  delimiter: ":",
  win32: null,
  posix: null
};
ft.win32 = et.win32 = et;
ft.posix = et.posix = ft;
In ? et.normalize : ft.normalize;
In ? et.resolve : ft.resolve;
In ? et.relative : ft.relative;
In ? et.dirname : ft.dirname;
In ? et.basename : ft.basename;
In ? et.extname : ft.extname;
In ? et.sep : ft.sep;
const q0 = /^\w[\w\d+.-]*$/, W0 = /^\//, H0 = /^\/\//;
function Y0(e, t) {
  if (!e.scheme && t)
    throw new Error(`[UriError]: Scheme is missing: {scheme: "", authority: "${e.authority}", path: "${e.path}", query: "${e.query}", fragment: "${e.fragment}"}`);
  if (e.scheme && !q0.test(e.scheme))
    throw new Error("[UriError]: Scheme contains illegal characters.");
  if (e.path) {
    if (e.authority) {
      if (!W0.test(e.path))
        throw new Error('[UriError]: If a URI contains an authority component, then the path component must either be empty or begin with a slash ("/") character');
    } else if (H0.test(e.path))
      throw new Error('[UriError]: If a URI does not contain an authority component, then the path cannot begin with two slash characters ("//")');
  }
}
function z0(e, t) {
  return !e && !t ? "file" : e;
}
function G0(e, t) {
  switch (e) {
    case "https":
    case "http":
    case "file":
      t ? t[0] !== Ot && (t = Ot + t) : t = Ot;
      break;
  }
  return t;
}
const Le = "", Ot = "/", J0 = /^(([^:/?#]+?):)?(\/\/([^/?#]*))?([^?#]*)(\?([^#]*))?(#(.*))?/;
let su = class Ci {
  static isUri(t) {
    return t instanceof Ci ? !0 : !t || typeof t != "object" ? !1 : typeof t.authority == "string" && typeof t.fragment == "string" && typeof t.path == "string" && typeof t.query == "string" && typeof t.scheme == "string" && typeof t.fsPath == "string" && typeof t.with == "function" && typeof t.toString == "function";
  }
  /**
   * @internal
   */
  constructor(t, n, r, s, i, a = !1) {
    typeof t == "object" ? (this.scheme = t.scheme || Le, this.authority = t.authority || Le, this.path = t.path || Le, this.query = t.query || Le, this.fragment = t.fragment || Le) : (this.scheme = z0(t, a), this.authority = n || Le, this.path = G0(this.scheme, r || Le), this.query = s || Le, this.fragment = i || Le, Y0(this, a));
  }
  // ---- filesystem path -----------------------
  /**
   * Returns a string representing the corresponding file system path of this URI.
   * Will handle UNC paths, normalizes windows drive letters to lower-case, and uses the
   * platform specific path separator.
   *
   * * Will *not* validate the path for invalid characters and semantics.
   * * Will *not* look at the scheme of this URI.
   * * The result shall *not* be used for display purposes but for accessing a file on disk.
   *
   *
   * The *difference* to `URI#path` is the use of the platform specific separator and the handling
   * of UNC paths. See the below sample of a file-uri with an authority (UNC path).
   *
   * ```ts
      const u = URI.parse('file://server/c$/folder/file.txt')
      u.authority === 'server'
      u.path === '/shares/c$/file.txt'
      u.fsPath === '\\server\c$\folder\file.txt'
  ```
   *
   * Using `URI#path` to read a file (using fs-apis) would not be enough because parts of the path,
   * namely the server name, would be missing. Therefore `URI#fsPath` exists - it's sugar to ease working
   * with URIs that represent files on disk (`file` scheme).
   */
  get fsPath() {
    return $o(this, !1);
  }
  // ---- modify to new -------------------------
  with(t) {
    if (!t)
      return this;
    let { scheme: n, authority: r, path: s, query: i, fragment: a } = t;
    return n === void 0 ? n = this.scheme : n === null && (n = Le), r === void 0 ? r = this.authority : r === null && (r = Le), s === void 0 ? s = this.path : s === null && (s = Le), i === void 0 ? i = this.query : i === null && (i = Le), a === void 0 ? a = this.fragment : a === null && (a = Le), n === this.scheme && r === this.authority && s === this.path && i === this.query && a === this.fragment ? this : new Sr(n, r, s, i, a);
  }
  // ---- parse & validate ------------------------
  /**
   * Creates a new URI from a string, e.g. `http://www.example.com/some/path`,
   * `file:///usr/home`, or `scheme:with/path`.
   *
   * @param value A string which represents an URI (see `URI#toString`).
   */
  static parse(t, n = !1) {
    const r = J0.exec(t);
    return r ? new Sr(r[2] || Le, ci(r[4] || Le), ci(r[5] || Le), ci(r[7] || Le), ci(r[9] || Le), n) : new Sr(Le, Le, Le, Le, Le);
  }
  /**
   * Creates a new URI from a file system path, e.g. `c:\my\files`,
   * `/usr/home`, or `\\server\share\some\path`.
   *
   * The *difference* between `URI#parse` and `URI#file` is that the latter treats the argument
   * as path, not as stringified-uri. E.g. `URI.file(path)` is **not the same as**
   * `URI.parse('file://' + path)` because the path might contain characters that are
   * interpreted (# and ?). See the following sample:
   * ```ts
  const good = URI.file('/coding/c#/project1');
  good.scheme === 'file';
  good.path === '/coding/c#/project1';
  good.fragment === '';
  const bad = URI.parse('file://' + '/coding/c#/project1');
  bad.scheme === 'file';
  bad.path === '/coding/c'; // path is now broken
  bad.fragment === '/project1';
  ```
   *
   * @param path A file system path (see `URI#fsPath`)
   */
  static file(t) {
    let n = Le;
    if (Ys && (t = t.replace(/\\/g, Ot)), t[0] === Ot && t[1] === Ot) {
      const r = t.indexOf(Ot, 2);
      r === -1 ? (n = t.substring(2), t = Ot) : (n = t.substring(2, r), t = t.substring(r) || Ot);
    }
    return new Sr("file", n, t, Le, Le);
  }
  /**
   * Creates new URI from uri components.
   *
   * Unless `strict` is `true` the scheme is defaults to be `file`. This function performs
   * validation and should be used for untrusted uri components retrieved from storage,
   * user input, command arguments etc
   */
  static from(t, n) {
    return new Sr(t.scheme, t.authority, t.path, t.query, t.fragment, n);
  }
  /**
   * Join a URI path with path fragments and normalizes the resulting path.
   *
   * @param uri The input URI.
   * @param pathFragment The path fragment to add to the URI path.
   * @returns The resulting URI.
   */
  static joinPath(t, ...n) {
    if (!t.path)
      throw new Error("[UriError]: cannot call joinPath on URI without path");
    let r;
    return Ys && t.scheme === "file" ? r = Ci.file(et.join($o(t, !0), ...n)).path : r = ft.join(t.path, ...n), t.with({ path: r });
  }
  // ---- printing/externalize ---------------------------
  /**
   * Creates a string representation for this URI. It's guaranteed that calling
   * `URI.parse` with the result of this function creates an URI which is equal
   * to this URI.
   *
   * * The result shall *not* be used for display purposes but for externalization or transport.
   * * The result will be encoded using the percentage encoding and encoding happens mostly
   * ignore the scheme-specific encoding rules.
   *
   * @param skipEncoding Do not encode the result, default is `false`
   */
  toString(t = !1) {
    return Bo(this, t);
  }
  toJSON() {
    return this;
  }
  static revive(t) {
    if (t) {
      if (t instanceof Ci)
        return t;
      {
        const n = new Sr(t);
        return n._formatted = t.external ?? null, n._fsPath = t._sep === f1 ? t.fsPath ?? null : null, n;
      }
    } else return t;
  }
};
const f1 = Ys ? 1 : void 0;
class Sr extends su {
  constructor() {
    super(...arguments), this._formatted = null, this._fsPath = null;
  }
  get fsPath() {
    return this._fsPath || (this._fsPath = $o(this, !1)), this._fsPath;
  }
  toString(t = !1) {
    return t ? Bo(this, !0) : (this._formatted || (this._formatted = Bo(this, !1)), this._formatted);
  }
  toJSON() {
    const t = {
      $mid: 1
      /* MarshalledId.Uri */
    };
    return this._fsPath && (t.fsPath = this._fsPath, t._sep = f1), this._formatted && (t.external = this._formatted), this.path && (t.path = this.path), this.scheme && (t.scheme = this.scheme), this.authority && (t.authority = this.authority), this.query && (t.query = this.query), this.fragment && (t.fragment = this.fragment), t;
  }
}
const h1 = {
  58: "%3A",
  // gen-delims
  47: "%2F",
  63: "%3F",
  35: "%23",
  91: "%5B",
  93: "%5D",
  64: "%40",
  33: "%21",
  // sub-delims
  36: "%24",
  38: "%26",
  39: "%27",
  40: "%28",
  41: "%29",
  42: "%2A",
  43: "%2B",
  44: "%2C",
  59: "%3B",
  61: "%3D",
  32: "%20"
};
function uc(e, t, n) {
  let r, s = -1;
  for (let i = 0; i < e.length; i++) {
    const a = e.charCodeAt(i);
    if (a >= 97 && a <= 122 || a >= 65 && a <= 90 || a >= 48 && a <= 57 || a === 45 || a === 46 || a === 95 || a === 126 || t && a === 47 || n && a === 91 || n && a === 93 || n && a === 58)
      s !== -1 && (r += encodeURIComponent(e.substring(s, i)), s = -1), r !== void 0 && (r += e.charAt(i));
    else {
      r === void 0 && (r = e.substr(0, i));
      const o = h1[a];
      o !== void 0 ? (s !== -1 && (r += encodeURIComponent(e.substring(s, i)), s = -1), r += o) : s === -1 && (s = i);
    }
  }
  return s !== -1 && (r += encodeURIComponent(e.substring(s))), r !== void 0 ? r : e;
}
function Q0(e) {
  let t;
  for (let n = 0; n < e.length; n++) {
    const r = e.charCodeAt(n);
    r === 35 || r === 63 ? (t === void 0 && (t = e.substr(0, n)), t += h1[r]) : t !== void 0 && (t += e[n]);
  }
  return t !== void 0 ? t : e;
}
function $o(e, t) {
  let n;
  return e.authority && e.path.length > 1 && e.scheme === "file" ? n = `//${e.authority}${e.path}` : e.path.charCodeAt(0) === 47 && (e.path.charCodeAt(1) >= 65 && e.path.charCodeAt(1) <= 90 || e.path.charCodeAt(1) >= 97 && e.path.charCodeAt(1) <= 122) && e.path.charCodeAt(2) === 58 ? t ? n = e.path.substr(1) : n = e.path[1].toLowerCase() + e.path.substr(2) : n = e.path, Ys && (n = n.replace(/\//g, "\\")), n;
}
function Bo(e, t) {
  const n = t ? Q0 : uc;
  let r = "", { scheme: s, authority: i, path: a, query: o, fragment: l } = e;
  if (s && (r += s, r += ":"), (i || s === "file") && (r += Ot, r += Ot), i) {
    let u = i.indexOf("@");
    if (u !== -1) {
      const f = i.substr(0, u);
      i = i.substr(u + 1), u = f.lastIndexOf(":"), u === -1 ? r += n(f, !1, !1) : (r += n(f.substr(0, u), !1, !1), r += ":", r += n(f.substr(u + 1), !1, !0)), r += "@";
    }
    i = i.toLowerCase(), u = i.lastIndexOf(":"), u === -1 ? r += n(i, !1, !0) : (r += n(i.substr(0, u), !1, !0), r += i.substr(u));
  }
  if (a) {
    if (a.length >= 3 && a.charCodeAt(0) === 47 && a.charCodeAt(2) === 58) {
      const u = a.charCodeAt(1);
      u >= 65 && u <= 90 && (a = `/${String.fromCharCode(u + 32)}:${a.substr(3)}`);
    } else if (a.length >= 2 && a.charCodeAt(1) === 58) {
      const u = a.charCodeAt(0);
      u >= 65 && u <= 90 && (a = `${String.fromCharCode(u + 32)}:${a.substr(2)}`);
    }
    r += n(a, !0, !1);
  }
  return o && (r += "?", r += n(o, !1, !1)), l && (r += "#", r += t ? l : uc(l, !1, !1)), r;
}
function d1(e) {
  try {
    return decodeURIComponent(e);
  } catch {
    return e.length > 3 ? e.substr(0, 3) + d1(e.substr(3)) : e;
  }
}
const cc = /(%[0-9A-Za-z][0-9A-Za-z])+/g;
function ci(e) {
  return e.match(cc) ? e.replace(cc, (t) => d1(t)) : e;
}
class dt extends fe {
  constructor(t, n, r, s) {
    super(t, n, r, s), this.selectionStartLineNumber = t, this.selectionStartColumn = n, this.positionLineNumber = r, this.positionColumn = s;
  }
  /**
   * Transform to a human-readable representation.
   */
  toString() {
    return "[" + this.selectionStartLineNumber + "," + this.selectionStartColumn + " -> " + this.positionLineNumber + "," + this.positionColumn + "]";
  }
  /**
   * Test if equals other selection.
   */
  equalsSelection(t) {
    return dt.selectionsEqual(this, t);
  }
  /**
   * Test if the two selections are equal.
   */
  static selectionsEqual(t, n) {
    return t.selectionStartLineNumber === n.selectionStartLineNumber && t.selectionStartColumn === n.selectionStartColumn && t.positionLineNumber === n.positionLineNumber && t.positionColumn === n.positionColumn;
  }
  /**
   * Get directions (LTR or RTL).
   */
  getDirection() {
    return this.selectionStartLineNumber === this.startLineNumber && this.selectionStartColumn === this.startColumn ? 0 : 1;
  }
  /**
   * Create a new selection with a different `positionLineNumber` and `positionColumn`.
   */
  setEndPosition(t, n) {
    return this.getDirection() === 0 ? new dt(this.startLineNumber, this.startColumn, t, n) : new dt(t, n, this.startLineNumber, this.startColumn);
  }
  /**
   * Get the position at `positionLineNumber` and `positionColumn`.
   */
  getPosition() {
    return new Ne(this.positionLineNumber, this.positionColumn);
  }
  /**
   * Get the position at the start of the selection.
  */
  getSelectionStart() {
    return new Ne(this.selectionStartLineNumber, this.selectionStartColumn);
  }
  /**
   * Create a new selection with a different `selectionStartLineNumber` and `selectionStartColumn`.
   */
  setStartPosition(t, n) {
    return this.getDirection() === 0 ? new dt(t, n, this.endLineNumber, this.endColumn) : new dt(this.endLineNumber, this.endColumn, t, n);
  }
  // ----
  /**
   * Create a `Selection` from one or two positions
   */
  static fromPositions(t, n = t) {
    return new dt(t.lineNumber, t.column, n.lineNumber, n.column);
  }
  /**
   * Creates a `Selection` from a range, given a direction.
   */
  static fromRange(t, n) {
    return n === 0 ? new dt(t.startLineNumber, t.startColumn, t.endLineNumber, t.endColumn) : new dt(t.endLineNumber, t.endColumn, t.startLineNumber, t.startColumn);
  }
  /**
   * Create a `Selection` from an `ISelection`.
   */
  static liftSelection(t) {
    return new dt(t.selectionStartLineNumber, t.selectionStartColumn, t.positionLineNumber, t.positionColumn);
  }
  /**
   * `a` equals `b`.
   */
  static selectionsArrEqual(t, n) {
    if (t && !n || !t && n)
      return !1;
    if (!t && !n)
      return !0;
    if (t.length !== n.length)
      return !1;
    for (let r = 0, s = t.length; r < s; r++)
      if (!this.selectionsEqual(t[r], n[r]))
        return !1;
    return !0;
  }
  /**
   * Test if `obj` is an `ISelection`.
   */
  static isISelection(t) {
    return t && typeof t.selectionStartLineNumber == "number" && typeof t.selectionStartColumn == "number" && typeof t.positionLineNumber == "number" && typeof t.positionColumn == "number";
  }
  /**
   * Create with a direction.
   */
  static createWithDirection(t, n, r, s, i) {
    return i === 0 ? new dt(t, n, r, s) : new dt(r, s, t, n);
  }
}
const fc = /* @__PURE__ */ Object.create(null);
function g(e, t) {
  if (Mg(t)) {
    const n = fc[t];
    if (n === void 0)
      throw new Error(`${e} references an unknown codicon: ${t}`);
    t = n;
  }
  return fc[e] = t, { id: e };
}
const K0 = {
  add: g("add", 6e4),
  plus: g("plus", 6e4),
  gistNew: g("gist-new", 6e4),
  repoCreate: g("repo-create", 6e4),
  lightbulb: g("lightbulb", 60001),
  lightBulb: g("light-bulb", 60001),
  repo: g("repo", 60002),
  repoDelete: g("repo-delete", 60002),
  gistFork: g("gist-fork", 60003),
  repoForked: g("repo-forked", 60003),
  gitPullRequest: g("git-pull-request", 60004),
  gitPullRequestAbandoned: g("git-pull-request-abandoned", 60004),
  recordKeys: g("record-keys", 60005),
  keyboard: g("keyboard", 60005),
  tag: g("tag", 60006),
  gitPullRequestLabel: g("git-pull-request-label", 60006),
  tagAdd: g("tag-add", 60006),
  tagRemove: g("tag-remove", 60006),
  person: g("person", 60007),
  personFollow: g("person-follow", 60007),
  personOutline: g("person-outline", 60007),
  personFilled: g("person-filled", 60007),
  gitBranch: g("git-branch", 60008),
  gitBranchCreate: g("git-branch-create", 60008),
  gitBranchDelete: g("git-branch-delete", 60008),
  sourceControl: g("source-control", 60008),
  mirror: g("mirror", 60009),
  mirrorPublic: g("mirror-public", 60009),
  star: g("star", 60010),
  starAdd: g("star-add", 60010),
  starDelete: g("star-delete", 60010),
  starEmpty: g("star-empty", 60010),
  comment: g("comment", 60011),
  commentAdd: g("comment-add", 60011),
  alert: g("alert", 60012),
  warning: g("warning", 60012),
  search: g("search", 60013),
  searchSave: g("search-save", 60013),
  logOut: g("log-out", 60014),
  signOut: g("sign-out", 60014),
  logIn: g("log-in", 60015),
  signIn: g("sign-in", 60015),
  eye: g("eye", 60016),
  eyeUnwatch: g("eye-unwatch", 60016),
  eyeWatch: g("eye-watch", 60016),
  circleFilled: g("circle-filled", 60017),
  primitiveDot: g("primitive-dot", 60017),
  closeDirty: g("close-dirty", 60017),
  debugBreakpoint: g("debug-breakpoint", 60017),
  debugBreakpointDisabled: g("debug-breakpoint-disabled", 60017),
  debugHint: g("debug-hint", 60017),
  terminalDecorationSuccess: g("terminal-decoration-success", 60017),
  primitiveSquare: g("primitive-square", 60018),
  edit: g("edit", 60019),
  pencil: g("pencil", 60019),
  info: g("info", 60020),
  issueOpened: g("issue-opened", 60020),
  gistPrivate: g("gist-private", 60021),
  gitForkPrivate: g("git-fork-private", 60021),
  lock: g("lock", 60021),
  mirrorPrivate: g("mirror-private", 60021),
  close: g("close", 60022),
  removeClose: g("remove-close", 60022),
  x: g("x", 60022),
  repoSync: g("repo-sync", 60023),
  sync: g("sync", 60023),
  clone: g("clone", 60024),
  desktopDownload: g("desktop-download", 60024),
  beaker: g("beaker", 60025),
  microscope: g("microscope", 60025),
  vm: g("vm", 60026),
  deviceDesktop: g("device-desktop", 60026),
  file: g("file", 60027),
  fileText: g("file-text", 60027),
  more: g("more", 60028),
  ellipsis: g("ellipsis", 60028),
  kebabHorizontal: g("kebab-horizontal", 60028),
  mailReply: g("mail-reply", 60029),
  reply: g("reply", 60029),
  organization: g("organization", 60030),
  organizationFilled: g("organization-filled", 60030),
  organizationOutline: g("organization-outline", 60030),
  newFile: g("new-file", 60031),
  fileAdd: g("file-add", 60031),
  newFolder: g("new-folder", 60032),
  fileDirectoryCreate: g("file-directory-create", 60032),
  trash: g("trash", 60033),
  trashcan: g("trashcan", 60033),
  history: g("history", 60034),
  clock: g("clock", 60034),
  folder: g("folder", 60035),
  fileDirectory: g("file-directory", 60035),
  symbolFolder: g("symbol-folder", 60035),
  logoGithub: g("logo-github", 60036),
  markGithub: g("mark-github", 60036),
  github: g("github", 60036),
  terminal: g("terminal", 60037),
  console: g("console", 60037),
  repl: g("repl", 60037),
  zap: g("zap", 60038),
  symbolEvent: g("symbol-event", 60038),
  error: g("error", 60039),
  stop: g("stop", 60039),
  variable: g("variable", 60040),
  symbolVariable: g("symbol-variable", 60040),
  array: g("array", 60042),
  symbolArray: g("symbol-array", 60042),
  symbolModule: g("symbol-module", 60043),
  symbolPackage: g("symbol-package", 60043),
  symbolNamespace: g("symbol-namespace", 60043),
  symbolObject: g("symbol-object", 60043),
  symbolMethod: g("symbol-method", 60044),
  symbolFunction: g("symbol-function", 60044),
  symbolConstructor: g("symbol-constructor", 60044),
  symbolBoolean: g("symbol-boolean", 60047),
  symbolNull: g("symbol-null", 60047),
  symbolNumeric: g("symbol-numeric", 60048),
  symbolNumber: g("symbol-number", 60048),
  symbolStructure: g("symbol-structure", 60049),
  symbolStruct: g("symbol-struct", 60049),
  symbolParameter: g("symbol-parameter", 60050),
  symbolTypeParameter: g("symbol-type-parameter", 60050),
  symbolKey: g("symbol-key", 60051),
  symbolText: g("symbol-text", 60051),
  symbolReference: g("symbol-reference", 60052),
  goToFile: g("go-to-file", 60052),
  symbolEnum: g("symbol-enum", 60053),
  symbolValue: g("symbol-value", 60053),
  symbolRuler: g("symbol-ruler", 60054),
  symbolUnit: g("symbol-unit", 60054),
  activateBreakpoints: g("activate-breakpoints", 60055),
  archive: g("archive", 60056),
  arrowBoth: g("arrow-both", 60057),
  arrowDown: g("arrow-down", 60058),
  arrowLeft: g("arrow-left", 60059),
  arrowRight: g("arrow-right", 60060),
  arrowSmallDown: g("arrow-small-down", 60061),
  arrowSmallLeft: g("arrow-small-left", 60062),
  arrowSmallRight: g("arrow-small-right", 60063),
  arrowSmallUp: g("arrow-small-up", 60064),
  arrowUp: g("arrow-up", 60065),
  bell: g("bell", 60066),
  bold: g("bold", 60067),
  book: g("book", 60068),
  bookmark: g("bookmark", 60069),
  debugBreakpointConditionalUnverified: g("debug-breakpoint-conditional-unverified", 60070),
  debugBreakpointConditional: g("debug-breakpoint-conditional", 60071),
  debugBreakpointConditionalDisabled: g("debug-breakpoint-conditional-disabled", 60071),
  debugBreakpointDataUnverified: g("debug-breakpoint-data-unverified", 60072),
  debugBreakpointData: g("debug-breakpoint-data", 60073),
  debugBreakpointDataDisabled: g("debug-breakpoint-data-disabled", 60073),
  debugBreakpointLogUnverified: g("debug-breakpoint-log-unverified", 60074),
  debugBreakpointLog: g("debug-breakpoint-log", 60075),
  debugBreakpointLogDisabled: g("debug-breakpoint-log-disabled", 60075),
  briefcase: g("briefcase", 60076),
  broadcast: g("broadcast", 60077),
  browser: g("browser", 60078),
  bug: g("bug", 60079),
  calendar: g("calendar", 60080),
  caseSensitive: g("case-sensitive", 60081),
  check: g("check", 60082),
  checklist: g("checklist", 60083),
  chevronDown: g("chevron-down", 60084),
  chevronLeft: g("chevron-left", 60085),
  chevronRight: g("chevron-right", 60086),
  chevronUp: g("chevron-up", 60087),
  chromeClose: g("chrome-close", 60088),
  chromeMaximize: g("chrome-maximize", 60089),
  chromeMinimize: g("chrome-minimize", 60090),
  chromeRestore: g("chrome-restore", 60091),
  circleOutline: g("circle-outline", 60092),
  circle: g("circle", 60092),
  debugBreakpointUnverified: g("debug-breakpoint-unverified", 60092),
  terminalDecorationIncomplete: g("terminal-decoration-incomplete", 60092),
  circleSlash: g("circle-slash", 60093),
  circuitBoard: g("circuit-board", 60094),
  clearAll: g("clear-all", 60095),
  clippy: g("clippy", 60096),
  closeAll: g("close-all", 60097),
  cloudDownload: g("cloud-download", 60098),
  cloudUpload: g("cloud-upload", 60099),
  code: g("code", 60100),
  collapseAll: g("collapse-all", 60101),
  colorMode: g("color-mode", 60102),
  commentDiscussion: g("comment-discussion", 60103),
  creditCard: g("credit-card", 60105),
  dash: g("dash", 60108),
  dashboard: g("dashboard", 60109),
  database: g("database", 60110),
  debugContinue: g("debug-continue", 60111),
  debugDisconnect: g("debug-disconnect", 60112),
  debugPause: g("debug-pause", 60113),
  debugRestart: g("debug-restart", 60114),
  debugStart: g("debug-start", 60115),
  debugStepInto: g("debug-step-into", 60116),
  debugStepOut: g("debug-step-out", 60117),
  debugStepOver: g("debug-step-over", 60118),
  debugStop: g("debug-stop", 60119),
  debug: g("debug", 60120),
  deviceCameraVideo: g("device-camera-video", 60121),
  deviceCamera: g("device-camera", 60122),
  deviceMobile: g("device-mobile", 60123),
  diffAdded: g("diff-added", 60124),
  diffIgnored: g("diff-ignored", 60125),
  diffModified: g("diff-modified", 60126),
  diffRemoved: g("diff-removed", 60127),
  diffRenamed: g("diff-renamed", 60128),
  diff: g("diff", 60129),
  diffSidebyside: g("diff-sidebyside", 60129),
  discard: g("discard", 60130),
  editorLayout: g("editor-layout", 60131),
  emptyWindow: g("empty-window", 60132),
  exclude: g("exclude", 60133),
  extensions: g("extensions", 60134),
  eyeClosed: g("eye-closed", 60135),
  fileBinary: g("file-binary", 60136),
  fileCode: g("file-code", 60137),
  fileMedia: g("file-media", 60138),
  filePdf: g("file-pdf", 60139),
  fileSubmodule: g("file-submodule", 60140),
  fileSymlinkDirectory: g("file-symlink-directory", 60141),
  fileSymlinkFile: g("file-symlink-file", 60142),
  fileZip: g("file-zip", 60143),
  files: g("files", 60144),
  filter: g("filter", 60145),
  flame: g("flame", 60146),
  foldDown: g("fold-down", 60147),
  foldUp: g("fold-up", 60148),
  fold: g("fold", 60149),
  folderActive: g("folder-active", 60150),
  folderOpened: g("folder-opened", 60151),
  gear: g("gear", 60152),
  gift: g("gift", 60153),
  gistSecret: g("gist-secret", 60154),
  gist: g("gist", 60155),
  gitCommit: g("git-commit", 60156),
  gitCompare: g("git-compare", 60157),
  compareChanges: g("compare-changes", 60157),
  gitMerge: g("git-merge", 60158),
  githubAction: g("github-action", 60159),
  githubAlt: g("github-alt", 60160),
  globe: g("globe", 60161),
  grabber: g("grabber", 60162),
  graph: g("graph", 60163),
  gripper: g("gripper", 60164),
  heart: g("heart", 60165),
  home: g("home", 60166),
  horizontalRule: g("horizontal-rule", 60167),
  hubot: g("hubot", 60168),
  inbox: g("inbox", 60169),
  issueReopened: g("issue-reopened", 60171),
  issues: g("issues", 60172),
  italic: g("italic", 60173),
  jersey: g("jersey", 60174),
  json: g("json", 60175),
  kebabVertical: g("kebab-vertical", 60176),
  key: g("key", 60177),
  law: g("law", 60178),
  lightbulbAutofix: g("lightbulb-autofix", 60179),
  linkExternal: g("link-external", 60180),
  link: g("link", 60181),
  listOrdered: g("list-ordered", 60182),
  listUnordered: g("list-unordered", 60183),
  liveShare: g("live-share", 60184),
  loading: g("loading", 60185),
  location: g("location", 60186),
  mailRead: g("mail-read", 60187),
  mail: g("mail", 60188),
  markdown: g("markdown", 60189),
  megaphone: g("megaphone", 60190),
  mention: g("mention", 60191),
  milestone: g("milestone", 60192),
  gitPullRequestMilestone: g("git-pull-request-milestone", 60192),
  mortarBoard: g("mortar-board", 60193),
  move: g("move", 60194),
  multipleWindows: g("multiple-windows", 60195),
  mute: g("mute", 60196),
  noNewline: g("no-newline", 60197),
  note: g("note", 60198),
  octoface: g("octoface", 60199),
  openPreview: g("open-preview", 60200),
  package: g("package", 60201),
  paintcan: g("paintcan", 60202),
  pin: g("pin", 60203),
  play: g("play", 60204),
  run: g("run", 60204),
  plug: g("plug", 60205),
  preserveCase: g("preserve-case", 60206),
  preview: g("preview", 60207),
  project: g("project", 60208),
  pulse: g("pulse", 60209),
  question: g("question", 60210),
  quote: g("quote", 60211),
  radioTower: g("radio-tower", 60212),
  reactions: g("reactions", 60213),
  references: g("references", 60214),
  refresh: g("refresh", 60215),
  regex: g("regex", 60216),
  remoteExplorer: g("remote-explorer", 60217),
  remote: g("remote", 60218),
  remove: g("remove", 60219),
  replaceAll: g("replace-all", 60220),
  replace: g("replace", 60221),
  repoClone: g("repo-clone", 60222),
  repoForcePush: g("repo-force-push", 60223),
  repoPull: g("repo-pull", 60224),
  repoPush: g("repo-push", 60225),
  report: g("report", 60226),
  requestChanges: g("request-changes", 60227),
  rocket: g("rocket", 60228),
  rootFolderOpened: g("root-folder-opened", 60229),
  rootFolder: g("root-folder", 60230),
  rss: g("rss", 60231),
  ruby: g("ruby", 60232),
  saveAll: g("save-all", 60233),
  saveAs: g("save-as", 60234),
  save: g("save", 60235),
  screenFull: g("screen-full", 60236),
  screenNormal: g("screen-normal", 60237),
  searchStop: g("search-stop", 60238),
  server: g("server", 60240),
  settingsGear: g("settings-gear", 60241),
  settings: g("settings", 60242),
  shield: g("shield", 60243),
  smiley: g("smiley", 60244),
  sortPrecedence: g("sort-precedence", 60245),
  splitHorizontal: g("split-horizontal", 60246),
  splitVertical: g("split-vertical", 60247),
  squirrel: g("squirrel", 60248),
  starFull: g("star-full", 60249),
  starHalf: g("star-half", 60250),
  symbolClass: g("symbol-class", 60251),
  symbolColor: g("symbol-color", 60252),
  symbolConstant: g("symbol-constant", 60253),
  symbolEnumMember: g("symbol-enum-member", 60254),
  symbolField: g("symbol-field", 60255),
  symbolFile: g("symbol-file", 60256),
  symbolInterface: g("symbol-interface", 60257),
  symbolKeyword: g("symbol-keyword", 60258),
  symbolMisc: g("symbol-misc", 60259),
  symbolOperator: g("symbol-operator", 60260),
  symbolProperty: g("symbol-property", 60261),
  wrench: g("wrench", 60261),
  wrenchSubaction: g("wrench-subaction", 60261),
  symbolSnippet: g("symbol-snippet", 60262),
  tasklist: g("tasklist", 60263),
  telescope: g("telescope", 60264),
  textSize: g("text-size", 60265),
  threeBars: g("three-bars", 60266),
  thumbsdown: g("thumbsdown", 60267),
  thumbsup: g("thumbsup", 60268),
  tools: g("tools", 60269),
  triangleDown: g("triangle-down", 60270),
  triangleLeft: g("triangle-left", 60271),
  triangleRight: g("triangle-right", 60272),
  triangleUp: g("triangle-up", 60273),
  twitter: g("twitter", 60274),
  unfold: g("unfold", 60275),
  unlock: g("unlock", 60276),
  unmute: g("unmute", 60277),
  unverified: g("unverified", 60278),
  verified: g("verified", 60279),
  versions: g("versions", 60280),
  vmActive: g("vm-active", 60281),
  vmOutline: g("vm-outline", 60282),
  vmRunning: g("vm-running", 60283),
  watch: g("watch", 60284),
  whitespace: g("whitespace", 60285),
  wholeWord: g("whole-word", 60286),
  window: g("window", 60287),
  wordWrap: g("word-wrap", 60288),
  zoomIn: g("zoom-in", 60289),
  zoomOut: g("zoom-out", 60290),
  listFilter: g("list-filter", 60291),
  listFlat: g("list-flat", 60292),
  listSelection: g("list-selection", 60293),
  selection: g("selection", 60293),
  listTree: g("list-tree", 60294),
  debugBreakpointFunctionUnverified: g("debug-breakpoint-function-unverified", 60295),
  debugBreakpointFunction: g("debug-breakpoint-function", 60296),
  debugBreakpointFunctionDisabled: g("debug-breakpoint-function-disabled", 60296),
  debugStackframeActive: g("debug-stackframe-active", 60297),
  circleSmallFilled: g("circle-small-filled", 60298),
  debugStackframeDot: g("debug-stackframe-dot", 60298),
  terminalDecorationMark: g("terminal-decoration-mark", 60298),
  debugStackframe: g("debug-stackframe", 60299),
  debugStackframeFocused: g("debug-stackframe-focused", 60299),
  debugBreakpointUnsupported: g("debug-breakpoint-unsupported", 60300),
  symbolString: g("symbol-string", 60301),
  debugReverseContinue: g("debug-reverse-continue", 60302),
  debugStepBack: g("debug-step-back", 60303),
  debugRestartFrame: g("debug-restart-frame", 60304),
  debugAlt: g("debug-alt", 60305),
  callIncoming: g("call-incoming", 60306),
  callOutgoing: g("call-outgoing", 60307),
  menu: g("menu", 60308),
  expandAll: g("expand-all", 60309),
  feedback: g("feedback", 60310),
  gitPullRequestReviewer: g("git-pull-request-reviewer", 60310),
  groupByRefType: g("group-by-ref-type", 60311),
  ungroupByRefType: g("ungroup-by-ref-type", 60312),
  account: g("account", 60313),
  gitPullRequestAssignee: g("git-pull-request-assignee", 60313),
  bellDot: g("bell-dot", 60314),
  debugConsole: g("debug-console", 60315),
  library: g("library", 60316),
  output: g("output", 60317),
  runAll: g("run-all", 60318),
  syncIgnored: g("sync-ignored", 60319),
  pinned: g("pinned", 60320),
  githubInverted: g("github-inverted", 60321),
  serverProcess: g("server-process", 60322),
  serverEnvironment: g("server-environment", 60323),
  pass: g("pass", 60324),
  issueClosed: g("issue-closed", 60324),
  stopCircle: g("stop-circle", 60325),
  playCircle: g("play-circle", 60326),
  record: g("record", 60327),
  debugAltSmall: g("debug-alt-small", 60328),
  vmConnect: g("vm-connect", 60329),
  cloud: g("cloud", 60330),
  merge: g("merge", 60331),
  export: g("export", 60332),
  graphLeft: g("graph-left", 60333),
  magnet: g("magnet", 60334),
  notebook: g("notebook", 60335),
  redo: g("redo", 60336),
  checkAll: g("check-all", 60337),
  pinnedDirty: g("pinned-dirty", 60338),
  passFilled: g("pass-filled", 60339),
  circleLargeFilled: g("circle-large-filled", 60340),
  circleLarge: g("circle-large", 60341),
  circleLargeOutline: g("circle-large-outline", 60341),
  combine: g("combine", 60342),
  gather: g("gather", 60342),
  table: g("table", 60343),
  variableGroup: g("variable-group", 60344),
  typeHierarchy: g("type-hierarchy", 60345),
  typeHierarchySub: g("type-hierarchy-sub", 60346),
  typeHierarchySuper: g("type-hierarchy-super", 60347),
  gitPullRequestCreate: g("git-pull-request-create", 60348),
  runAbove: g("run-above", 60349),
  runBelow: g("run-below", 60350),
  notebookTemplate: g("notebook-template", 60351),
  debugRerun: g("debug-rerun", 60352),
  workspaceTrusted: g("workspace-trusted", 60353),
  workspaceUntrusted: g("workspace-untrusted", 60354),
  workspaceUnknown: g("workspace-unknown", 60355),
  terminalCmd: g("terminal-cmd", 60356),
  terminalDebian: g("terminal-debian", 60357),
  terminalLinux: g("terminal-linux", 60358),
  terminalPowershell: g("terminal-powershell", 60359),
  terminalTmux: g("terminal-tmux", 60360),
  terminalUbuntu: g("terminal-ubuntu", 60361),
  terminalBash: g("terminal-bash", 60362),
  arrowSwap: g("arrow-swap", 60363),
  copy: g("copy", 60364),
  personAdd: g("person-add", 60365),
  filterFilled: g("filter-filled", 60366),
  wand: g("wand", 60367),
  debugLineByLine: g("debug-line-by-line", 60368),
  inspect: g("inspect", 60369),
  layers: g("layers", 60370),
  layersDot: g("layers-dot", 60371),
  layersActive: g("layers-active", 60372),
  compass: g("compass", 60373),
  compassDot: g("compass-dot", 60374),
  compassActive: g("compass-active", 60375),
  azure: g("azure", 60376),
  issueDraft: g("issue-draft", 60377),
  gitPullRequestClosed: g("git-pull-request-closed", 60378),
  gitPullRequestDraft: g("git-pull-request-draft", 60379),
  debugAll: g("debug-all", 60380),
  debugCoverage: g("debug-coverage", 60381),
  runErrors: g("run-errors", 60382),
  folderLibrary: g("folder-library", 60383),
  debugContinueSmall: g("debug-continue-small", 60384),
  beakerStop: g("beaker-stop", 60385),
  graphLine: g("graph-line", 60386),
  graphScatter: g("graph-scatter", 60387),
  pieChart: g("pie-chart", 60388),
  bracket: g("bracket", 60175),
  bracketDot: g("bracket-dot", 60389),
  bracketError: g("bracket-error", 60390),
  lockSmall: g("lock-small", 60391),
  azureDevops: g("azure-devops", 60392),
  verifiedFilled: g("verified-filled", 60393),
  newline: g("newline", 60394),
  layout: g("layout", 60395),
  layoutActivitybarLeft: g("layout-activitybar-left", 60396),
  layoutActivitybarRight: g("layout-activitybar-right", 60397),
  layoutPanelLeft: g("layout-panel-left", 60398),
  layoutPanelCenter: g("layout-panel-center", 60399),
  layoutPanelJustify: g("layout-panel-justify", 60400),
  layoutPanelRight: g("layout-panel-right", 60401),
  layoutPanel: g("layout-panel", 60402),
  layoutSidebarLeft: g("layout-sidebar-left", 60403),
  layoutSidebarRight: g("layout-sidebar-right", 60404),
  layoutStatusbar: g("layout-statusbar", 60405),
  layoutMenubar: g("layout-menubar", 60406),
  layoutCentered: g("layout-centered", 60407),
  target: g("target", 60408),
  indent: g("indent", 60409),
  recordSmall: g("record-small", 60410),
  errorSmall: g("error-small", 60411),
  terminalDecorationError: g("terminal-decoration-error", 60411),
  arrowCircleDown: g("arrow-circle-down", 60412),
  arrowCircleLeft: g("arrow-circle-left", 60413),
  arrowCircleRight: g("arrow-circle-right", 60414),
  arrowCircleUp: g("arrow-circle-up", 60415),
  layoutSidebarRightOff: g("layout-sidebar-right-off", 60416),
  layoutPanelOff: g("layout-panel-off", 60417),
  layoutSidebarLeftOff: g("layout-sidebar-left-off", 60418),
  blank: g("blank", 60419),
  heartFilled: g("heart-filled", 60420),
  map: g("map", 60421),
  mapHorizontal: g("map-horizontal", 60421),
  foldHorizontal: g("fold-horizontal", 60421),
  mapFilled: g("map-filled", 60422),
  mapHorizontalFilled: g("map-horizontal-filled", 60422),
  foldHorizontalFilled: g("fold-horizontal-filled", 60422),
  circleSmall: g("circle-small", 60423),
  bellSlash: g("bell-slash", 60424),
  bellSlashDot: g("bell-slash-dot", 60425),
  commentUnresolved: g("comment-unresolved", 60426),
  gitPullRequestGoToChanges: g("git-pull-request-go-to-changes", 60427),
  gitPullRequestNewChanges: g("git-pull-request-new-changes", 60428),
  searchFuzzy: g("search-fuzzy", 60429),
  commentDraft: g("comment-draft", 60430),
  send: g("send", 60431),
  sparkle: g("sparkle", 60432),
  insert: g("insert", 60433),
  mic: g("mic", 60434),
  thumbsdownFilled: g("thumbsdown-filled", 60435),
  thumbsupFilled: g("thumbsup-filled", 60436),
  coffee: g("coffee", 60437),
  snake: g("snake", 60438),
  game: g("game", 60439),
  vr: g("vr", 60440),
  chip: g("chip", 60441),
  piano: g("piano", 60442),
  music: g("music", 60443),
  micFilled: g("mic-filled", 60444),
  repoFetch: g("repo-fetch", 60445),
  copilot: g("copilot", 60446),
  lightbulbSparkle: g("lightbulb-sparkle", 60447),
  robot: g("robot", 60448),
  sparkleFilled: g("sparkle-filled", 60449),
  diffSingle: g("diff-single", 60450),
  diffMultiple: g("diff-multiple", 60451),
  surroundWith: g("surround-with", 60452),
  share: g("share", 60453),
  gitStash: g("git-stash", 60454),
  gitStashApply: g("git-stash-apply", 60455),
  gitStashPop: g("git-stash-pop", 60456),
  vscode: g("vscode", 60457),
  vscodeInsiders: g("vscode-insiders", 60458),
  codeOss: g("code-oss", 60459),
  runCoverage: g("run-coverage", 60460),
  runAllCoverage: g("run-all-coverage", 60461),
  coverage: g("coverage", 60462),
  githubProject: g("github-project", 60463),
  mapVertical: g("map-vertical", 60464),
  foldVertical: g("fold-vertical", 60464),
  mapVerticalFilled: g("map-vertical-filled", 60465),
  foldVerticalFilled: g("fold-vertical-filled", 60465),
  goToSearch: g("go-to-search", 60466),
  percentage: g("percentage", 60467),
  sortPercentage: g("sort-percentage", 60467),
  attach: g("attach", 60468),
  goToEditingSession: g("go-to-editing-session", 60469),
  editSession: g("edit-session", 60470),
  codeReview: g("code-review", 60471),
  copilotWarning: g("copilot-warning", 60472),
  python: g("python", 60473),
  copilotLarge: g("copilot-large", 60474),
  copilotWarningLarge: g("copilot-warning-large", 60475),
  keyboardTab: g("keyboard-tab", 60476),
  copilotBlocked: g("copilot-blocked", 60477),
  copilotNotConnected: g("copilot-not-connected", 60478),
  flag: g("flag", 60479),
  lightbulbEmpty: g("lightbulb-empty", 60480),
  symbolMethodArrow: g("symbol-method-arrow", 60481),
  copilotUnavailable: g("copilot-unavailable", 60482),
  repoPinned: g("repo-pinned", 60483),
  keyboardTabAbove: g("keyboard-tab-above", 60484),
  keyboardTabBelow: g("keyboard-tab-below", 60485),
  gitPullRequestDone: g("git-pull-request-done", 60486),
  mcp: g("mcp", 60487),
  extensionsLarge: g("extensions-large", 60488),
  layoutPanelDock: g("layout-panel-dock", 60489),
  layoutSidebarLeftDock: g("layout-sidebar-left-dock", 60490),
  layoutSidebarRightDock: g("layout-sidebar-right-dock", 60491),
  copilotInProgress: g("copilot-in-progress", 60492),
  copilotError: g("copilot-error", 60493),
  copilotSuccess: g("copilot-success", 60494),
  chatSparkle: g("chat-sparkle", 60495),
  searchSparkle: g("search-sparkle", 60496),
  editSparkle: g("edit-sparkle", 60497),
  copilotSnooze: g("copilot-snooze", 60498),
  sendToRemoteAgent: g("send-to-remote-agent", 60499),
  commentDiscussionSparkle: g("comment-discussion-sparkle", 60500),
  chatSparkleWarning: g("chat-sparkle-warning", 60501),
  chatSparkleError: g("chat-sparkle-error", 60502),
  collection: g("collection", 60503),
  newCollection: g("new-collection", 60504),
  thinking: g("thinking", 60505)
}, X0 = {
  dialogError: g("dialog-error", "error"),
  dialogWarning: g("dialog-warning", "warning"),
  dialogInfo: g("dialog-info", "info"),
  dialogClose: g("dialog-close", "close"),
  treeItemExpanded: g("tree-item-expanded", "chevron-down"),
  // collapsed is done with rotation
  treeFilterOnTypeOn: g("tree-filter-on-type-on", "list-filter"),
  treeFilterOnTypeOff: g("tree-filter-on-type-off", "list-selection"),
  treeFilterClear: g("tree-filter-clear", "close"),
  treeItemLoading: g("tree-item-loading", "loading"),
  menuSelection: g("menu-selection", "check"),
  menuSubmenu: g("menu-submenu", "chevron-right"),
  menuBarMore: g("menubar-more", "more"),
  scrollbarButtonLeft: g("scrollbar-button-left", "triangle-left"),
  scrollbarButtonRight: g("scrollbar-button-right", "triangle-right"),
  scrollbarButtonUp: g("scrollbar-button-up", "triangle-up"),
  scrollbarButtonDown: g("scrollbar-button-down", "triangle-down"),
  toolBarMore: g("toolbar-more", "more"),
  quickInputBack: g("quick-input-back", "arrow-left"),
  dropDownButton: g("drop-down-button", 60084),
  symbolCustomColor: g("symbol-customcolor", 60252),
  exportIcon: g("export", 60332),
  workspaceUnspecified: g("workspace-unspecified", 60355),
  newLine: g("newline", 60394),
  thumbsDownFilled: g("thumbsdown-filled", 60435),
  thumbsUpFilled: g("thumbsup-filled", 60436),
  gitFetch: g("git-fetch", 60445),
  lightbulbSparkleAutofix: g("lightbulb-sparkle-autofix", 60447),
  debugBreakpointPending: g("debug-breakpoint-pending", 60377)
}, te = {
  ...K0,
  ...X0
};
class Z0 {
  constructor() {
    this._tokenizationSupports = /* @__PURE__ */ new Map(), this._factories = /* @__PURE__ */ new Map(), this._onDidChange = new Ht(), this.onDidChange = this._onDidChange.event, this._colorMap = null;
  }
  handleChange(t) {
    this._onDidChange.fire({
      changedLanguages: t,
      changedColorMap: !1
    });
  }
  register(t, n) {
    return this._tokenizationSupports.set(t, n), this.handleChange([t]), Yi(() => {
      this._tokenizationSupports.get(t) === n && (this._tokenizationSupports.delete(t), this.handleChange([t]));
    });
  }
  get(t) {
    return this._tokenizationSupports.get(t) || null;
  }
  registerFactory(t, n) {
    this._factories.get(t)?.dispose();
    const r = new ey(this, t, n);
    return this._factories.set(t, r), Yi(() => {
      const s = this._factories.get(t);
      !s || s !== r || (this._factories.delete(t), s.dispose());
    });
  }
  async getOrCreate(t) {
    const n = this.get(t);
    if (n)
      return n;
    const r = this._factories.get(t);
    return !r || r.isResolved ? null : (await r.resolve(), this.get(t));
  }
  isResolved(t) {
    if (this.get(t))
      return !0;
    const r = this._factories.get(t);
    return !!(!r || r.isResolved);
  }
  setColorMap(t) {
    this._colorMap = t, this._onDidChange.fire({
      changedLanguages: Array.from(this._tokenizationSupports.keys()),
      changedColorMap: !0
    });
  }
  getColorMap() {
    return this._colorMap;
  }
  getDefaultBackground() {
    return this._colorMap && this._colorMap.length > 2 ? this._colorMap[
      2
      /* ColorId.DefaultBackground */
    ] : null;
  }
}
class ey extends sr {
  get isResolved() {
    return this._isResolved;
  }
  constructor(t, n, r) {
    super(), this._registry = t, this._languageId = n, this._factory = r, this._isDisposed = !1, this._resolvePromise = null, this._isResolved = !1;
  }
  dispose() {
    this._isDisposed = !0, super.dispose();
  }
  async resolve() {
    return this._resolvePromise || (this._resolvePromise = this._create()), this._resolvePromise;
  }
  async _create() {
    const t = await this._factory.tokenizationSupport;
    this._isResolved = !0, t && !this._isDisposed && this._register(this._registry.register(this._languageId, t));
  }
}
class ty {
  constructor(t, n, r) {
    this.offset = t, this.type = n, this.language = r, this._tokenBrand = void 0;
  }
  toString() {
    return "(" + this.offset + ", " + this.type + ")";
  }
}
var hc;
(function(e) {
  e[e.Increase = 0] = "Increase", e[e.Decrease = 1] = "Decrease";
})(hc || (hc = {}));
var dc;
(function(e) {
  const t = /* @__PURE__ */ new Map();
  t.set(0, te.symbolMethod), t.set(1, te.symbolFunction), t.set(2, te.symbolConstructor), t.set(3, te.symbolField), t.set(4, te.symbolVariable), t.set(5, te.symbolClass), t.set(6, te.symbolStruct), t.set(7, te.symbolInterface), t.set(8, te.symbolModule), t.set(9, te.symbolProperty), t.set(10, te.symbolEvent), t.set(11, te.symbolOperator), t.set(12, te.symbolUnit), t.set(13, te.symbolValue), t.set(15, te.symbolEnum), t.set(14, te.symbolConstant), t.set(15, te.symbolEnum), t.set(16, te.symbolEnumMember), t.set(17, te.symbolKeyword), t.set(28, te.symbolSnippet), t.set(18, te.symbolText), t.set(19, te.symbolColor), t.set(20, te.symbolFile), t.set(21, te.symbolReference), t.set(22, te.symbolCustomColor), t.set(23, te.symbolFolder), t.set(24, te.symbolTypeParameter), t.set(25, te.account), t.set(26, te.issues), t.set(27, te.tools);
  function n(a) {
    let o = t.get(a);
    return o || (console.info("No codicon found for CompletionItemKind " + a), o = te.symbolProperty), o;
  }
  e.toIcon = n;
  function r(a) {
    switch (a) {
      case 0:
        return re(724, "Method");
      case 1:
        return re(725, "Function");
      case 2:
        return re(726, "Constructor");
      case 3:
        return re(727, "Field");
      case 4:
        return re(728, "Variable");
      case 5:
        return re(729, "Class");
      case 6:
        return re(730, "Struct");
      case 7:
        return re(731, "Interface");
      case 8:
        return re(732, "Module");
      case 9:
        return re(733, "Property");
      case 10:
        return re(734, "Event");
      case 11:
        return re(735, "Operator");
      case 12:
        return re(736, "Unit");
      case 13:
        return re(737, "Value");
      case 14:
        return re(738, "Constant");
      case 15:
        return re(739, "Enum");
      case 16:
        return re(740, "Enum Member");
      case 17:
        return re(741, "Keyword");
      case 18:
        return re(742, "Text");
      case 19:
        return re(743, "Color");
      case 20:
        return re(744, "File");
      case 21:
        return re(745, "Reference");
      case 22:
        return re(746, "Custom Color");
      case 23:
        return re(747, "Folder");
      case 24:
        return re(748, "Type Parameter");
      case 25:
        return re(749, "User");
      case 26:
        return re(750, "Issue");
      case 27:
        return re(751, "Tool");
      case 28:
        return re(752, "Snippet");
      default:
        return "";
    }
  }
  e.toLabel = r;
  const s = /* @__PURE__ */ new Map();
  s.set(
    "method",
    0
    /* CompletionItemKind.Method */
  ), s.set(
    "function",
    1
    /* CompletionItemKind.Function */
  ), s.set(
    "constructor",
    2
    /* CompletionItemKind.Constructor */
  ), s.set(
    "field",
    3
    /* CompletionItemKind.Field */
  ), s.set(
    "variable",
    4
    /* CompletionItemKind.Variable */
  ), s.set(
    "class",
    5
    /* CompletionItemKind.Class */
  ), s.set(
    "struct",
    6
    /* CompletionItemKind.Struct */
  ), s.set(
    "interface",
    7
    /* CompletionItemKind.Interface */
  ), s.set(
    "module",
    8
    /* CompletionItemKind.Module */
  ), s.set(
    "property",
    9
    /* CompletionItemKind.Property */
  ), s.set(
    "event",
    10
    /* CompletionItemKind.Event */
  ), s.set(
    "operator",
    11
    /* CompletionItemKind.Operator */
  ), s.set(
    "unit",
    12
    /* CompletionItemKind.Unit */
  ), s.set(
    "value",
    13
    /* CompletionItemKind.Value */
  ), s.set(
    "constant",
    14
    /* CompletionItemKind.Constant */
  ), s.set(
    "enum",
    15
    /* CompletionItemKind.Enum */
  ), s.set(
    "enum-member",
    16
    /* CompletionItemKind.EnumMember */
  ), s.set(
    "enumMember",
    16
    /* CompletionItemKind.EnumMember */
  ), s.set(
    "keyword",
    17
    /* CompletionItemKind.Keyword */
  ), s.set(
    "snippet",
    28
    /* CompletionItemKind.Snippet */
  ), s.set(
    "text",
    18
    /* CompletionItemKind.Text */
  ), s.set(
    "color",
    19
    /* CompletionItemKind.Color */
  ), s.set(
    "file",
    20
    /* CompletionItemKind.File */
  ), s.set(
    "reference",
    21
    /* CompletionItemKind.Reference */
  ), s.set(
    "customcolor",
    22
    /* CompletionItemKind.Customcolor */
  ), s.set(
    "folder",
    23
    /* CompletionItemKind.Folder */
  ), s.set(
    "type-parameter",
    24
    /* CompletionItemKind.TypeParameter */
  ), s.set(
    "typeParameter",
    24
    /* CompletionItemKind.TypeParameter */
  ), s.set(
    "account",
    25
    /* CompletionItemKind.User */
  ), s.set(
    "issue",
    26
    /* CompletionItemKind.Issue */
  ), s.set(
    "tool",
    27
    /* CompletionItemKind.Tool */
  );
  function i(a, o) {
    let l = s.get(a);
    return typeof l > "u" && !o && (l = 9), l;
  }
  e.fromString = i;
})(dc || (dc = {}));
var mc;
(function(e) {
  e[e.Automatic = 0] = "Automatic", e[e.Explicit = 1] = "Explicit";
})(mc || (mc = {}));
var pc;
(function(e) {
  e[e.Code = 1] = "Code", e[e.Label = 2] = "Label";
})(pc || (pc = {}));
var gc;
(function(e) {
  e[e.Accepted = 0] = "Accepted", e[e.Rejected = 1] = "Rejected", e[e.Ignored = 2] = "Ignored";
})(gc || (gc = {}));
var yc;
(function(e) {
  e[e.Automatic = 0] = "Automatic", e[e.PasteAs = 1] = "PasteAs";
})(yc || (yc = {}));
var bc;
(function(e) {
  e[e.Invoke = 1] = "Invoke", e[e.TriggerCharacter = 2] = "TriggerCharacter", e[e.ContentChange = 3] = "ContentChange";
})(bc || (bc = {}));
var vc;
(function(e) {
  e[e.Text = 0] = "Text", e[e.Read = 1] = "Read", e[e.Write = 2] = "Write";
})(vc || (vc = {}));
re(753, "array"), re(754, "boolean"), re(755, "class"), re(756, "constant"), re(757, "constructor"), re(758, "enumeration"), re(759, "enumeration member"), re(760, "event"), re(761, "field"), re(762, "file"), re(763, "function"), re(764, "interface"), re(765, "key"), re(766, "method"), re(767, "module"), re(768, "namespace"), re(769, "null"), re(770, "number"), re(771, "object"), re(772, "operator"), re(773, "package"), re(774, "property"), re(775, "string"), re(776, "struct"), re(777, "type parameter"), re(778, "variable");
var wc;
(function(e) {
  const t = /* @__PURE__ */ new Map();
  t.set(0, te.symbolFile), t.set(1, te.symbolModule), t.set(2, te.symbolNamespace), t.set(3, te.symbolPackage), t.set(4, te.symbolClass), t.set(5, te.symbolMethod), t.set(6, te.symbolProperty), t.set(7, te.symbolField), t.set(8, te.symbolConstructor), t.set(9, te.symbolEnum), t.set(10, te.symbolInterface), t.set(11, te.symbolFunction), t.set(12, te.symbolVariable), t.set(13, te.symbolConstant), t.set(14, te.symbolString), t.set(15, te.symbolNumber), t.set(16, te.symbolBoolean), t.set(17, te.symbolArray), t.set(18, te.symbolObject), t.set(19, te.symbolKey), t.set(20, te.symbolNull), t.set(21, te.symbolEnumMember), t.set(22, te.symbolStruct), t.set(23, te.symbolEvent), t.set(24, te.symbolOperator), t.set(25, te.symbolTypeParameter);
  function n(i) {
    let a = t.get(i);
    return a || (console.info("No codicon found for SymbolKind " + i), a = te.symbolProperty), a;
  }
  e.toIcon = n;
  const r = /* @__PURE__ */ new Map();
  r.set(
    0,
    20
    /* CompletionItemKind.File */
  ), r.set(
    1,
    8
    /* CompletionItemKind.Module */
  ), r.set(
    2,
    8
    /* CompletionItemKind.Module */
  ), r.set(
    3,
    8
    /* CompletionItemKind.Module */
  ), r.set(
    4,
    5
    /* CompletionItemKind.Class */
  ), r.set(
    5,
    0
    /* CompletionItemKind.Method */
  ), r.set(
    6,
    9
    /* CompletionItemKind.Property */
  ), r.set(
    7,
    3
    /* CompletionItemKind.Field */
  ), r.set(
    8,
    2
    /* CompletionItemKind.Constructor */
  ), r.set(
    9,
    15
    /* CompletionItemKind.Enum */
  ), r.set(
    10,
    7
    /* CompletionItemKind.Interface */
  ), r.set(
    11,
    1
    /* CompletionItemKind.Function */
  ), r.set(
    12,
    4
    /* CompletionItemKind.Variable */
  ), r.set(
    13,
    14
    /* CompletionItemKind.Constant */
  ), r.set(
    14,
    18
    /* CompletionItemKind.Text */
  ), r.set(
    15,
    13
    /* CompletionItemKind.Value */
  ), r.set(
    16,
    13
    /* CompletionItemKind.Value */
  ), r.set(
    17,
    13
    /* CompletionItemKind.Value */
  ), r.set(
    18,
    13
    /* CompletionItemKind.Value */
  ), r.set(
    19,
    17
    /* CompletionItemKind.Keyword */
  ), r.set(
    20,
    13
    /* CompletionItemKind.Value */
  ), r.set(
    21,
    16
    /* CompletionItemKind.EnumMember */
  ), r.set(
    22,
    6
    /* CompletionItemKind.Struct */
  ), r.set(
    23,
    10
    /* CompletionItemKind.Event */
  ), r.set(
    24,
    11
    /* CompletionItemKind.Operator */
  ), r.set(
    25,
    24
    /* CompletionItemKind.TypeParameter */
  );
  function s(i) {
    let a = r.get(i);
    return a === void 0 && (console.info("No completion kind found for SymbolKind " + i), a = 20), a;
  }
  e.toCompletionKind = s;
})(wc || (wc = {}));
var Ke;
let C6 = (Ke = class {
  /**
   * Returns a {@link FoldingRangeKind} for the given value.
   *
   * @param value of the kind.
   */
  static fromValue(t) {
    switch (t) {
      case "comment":
        return Ke.Comment;
      case "imports":
        return Ke.Imports;
      case "region":
        return Ke.Region;
    }
    return new Ke(t);
  }
  /**
   * Creates a new {@link FoldingRangeKind}.
   *
   * @param value of the kind.
   */
  constructor(t) {
    this.value = t;
  }
}, Ke.Comment = new Ke("comment"), Ke.Imports = new Ke("imports"), Ke.Region = new Ke("region"), Ke);
var Dc;
(function(e) {
  e[e.AIGenerated = 1] = "AIGenerated";
})(Dc || (Dc = {}));
var Sc;
(function(e) {
  e[e.Invoke = 0] = "Invoke", e[e.Automatic = 1] = "Automatic";
})(Sc || (Sc = {}));
var Ec;
(function(e) {
  function t(n) {
    return !n || typeof n != "object" ? !1 : typeof n.id == "string" && typeof n.title == "string";
  }
  e.is = t;
})(Ec || (Ec = {}));
var Ac;
(function(e) {
  e[e.Type = 1] = "Type", e[e.Parameter = 2] = "Parameter";
})(Ac || (Ac = {}));
new Z0();
var xc;
(function(e) {
  e[e.Unknown = 0] = "Unknown", e[e.Disabled = 1] = "Disabled", e[e.Enabled = 2] = "Enabled";
})(xc || (xc = {}));
var Nc;
(function(e) {
  e[e.Invoke = 1] = "Invoke", e[e.Auto = 2] = "Auto";
})(Nc || (Nc = {}));
var Lc;
(function(e) {
  e[e.None = 0] = "None", e[e.KeepWhitespace = 1] = "KeepWhitespace", e[e.InsertAsSnippet = 4] = "InsertAsSnippet";
})(Lc || (Lc = {}));
var kc;
(function(e) {
  e[e.Method = 0] = "Method", e[e.Function = 1] = "Function", e[e.Constructor = 2] = "Constructor", e[e.Field = 3] = "Field", e[e.Variable = 4] = "Variable", e[e.Class = 5] = "Class", e[e.Struct = 6] = "Struct", e[e.Interface = 7] = "Interface", e[e.Module = 8] = "Module", e[e.Property = 9] = "Property", e[e.Event = 10] = "Event", e[e.Operator = 11] = "Operator", e[e.Unit = 12] = "Unit", e[e.Value = 13] = "Value", e[e.Constant = 14] = "Constant", e[e.Enum = 15] = "Enum", e[e.EnumMember = 16] = "EnumMember", e[e.Keyword = 17] = "Keyword", e[e.Text = 18] = "Text", e[e.Color = 19] = "Color", e[e.File = 20] = "File", e[e.Reference = 21] = "Reference", e[e.Customcolor = 22] = "Customcolor", e[e.Folder = 23] = "Folder", e[e.TypeParameter = 24] = "TypeParameter", e[e.User = 25] = "User", e[e.Issue = 26] = "Issue", e[e.Tool = 27] = "Tool", e[e.Snippet = 28] = "Snippet";
})(kc || (kc = {}));
var Cc;
(function(e) {
  e[e.Deprecated = 1] = "Deprecated";
})(Cc || (Cc = {}));
var Fc;
(function(e) {
  e[e.Invoke = 0] = "Invoke", e[e.TriggerCharacter = 1] = "TriggerCharacter", e[e.TriggerForIncompleteCompletions = 2] = "TriggerForIncompleteCompletions";
})(Fc || (Fc = {}));
var _c;
(function(e) {
  e[e.EXACT = 0] = "EXACT", e[e.ABOVE = 1] = "ABOVE", e[e.BELOW = 2] = "BELOW";
})(_c || (_c = {}));
var Tc;
(function(e) {
  e[e.NotSet = 0] = "NotSet", e[e.ContentFlush = 1] = "ContentFlush", e[e.RecoverFromMarkers = 2] = "RecoverFromMarkers", e[e.Explicit = 3] = "Explicit", e[e.Paste = 4] = "Paste", e[e.Undo = 5] = "Undo", e[e.Redo = 6] = "Redo";
})(Tc || (Tc = {}));
var Mc;
(function(e) {
  e[e.LF = 1] = "LF", e[e.CRLF = 2] = "CRLF";
})(Mc || (Mc = {}));
var Oc;
(function(e) {
  e[e.Text = 0] = "Text", e[e.Read = 1] = "Read", e[e.Write = 2] = "Write";
})(Oc || (Oc = {}));
var Rc;
(function(e) {
  e[e.None = 0] = "None", e[e.Keep = 1] = "Keep", e[e.Brackets = 2] = "Brackets", e[e.Advanced = 3] = "Advanced", e[e.Full = 4] = "Full";
})(Rc || (Rc = {}));
var Pc;
(function(e) {
  e[e.acceptSuggestionOnCommitCharacter = 0] = "acceptSuggestionOnCommitCharacter", e[e.acceptSuggestionOnEnter = 1] = "acceptSuggestionOnEnter", e[e.accessibilitySupport = 2] = "accessibilitySupport", e[e.accessibilityPageSize = 3] = "accessibilityPageSize", e[e.allowOverflow = 4] = "allowOverflow", e[e.allowVariableLineHeights = 5] = "allowVariableLineHeights", e[e.allowVariableFonts = 6] = "allowVariableFonts", e[e.allowVariableFontsInAccessibilityMode = 7] = "allowVariableFontsInAccessibilityMode", e[e.ariaLabel = 8] = "ariaLabel", e[e.ariaRequired = 9] = "ariaRequired", e[e.autoClosingBrackets = 10] = "autoClosingBrackets", e[e.autoClosingComments = 11] = "autoClosingComments", e[e.screenReaderAnnounceInlineSuggestion = 12] = "screenReaderAnnounceInlineSuggestion", e[e.autoClosingDelete = 13] = "autoClosingDelete", e[e.autoClosingOvertype = 14] = "autoClosingOvertype", e[e.autoClosingQuotes = 15] = "autoClosingQuotes", e[e.autoIndent = 16] = "autoIndent", e[e.autoIndentOnPaste = 17] = "autoIndentOnPaste", e[e.autoIndentOnPasteWithinString = 18] = "autoIndentOnPasteWithinString", e[e.automaticLayout = 19] = "automaticLayout", e[e.autoSurround = 20] = "autoSurround", e[e.bracketPairColorization = 21] = "bracketPairColorization", e[e.guides = 22] = "guides", e[e.codeLens = 23] = "codeLens", e[e.codeLensFontFamily = 24] = "codeLensFontFamily", e[e.codeLensFontSize = 25] = "codeLensFontSize", e[e.colorDecorators = 26] = "colorDecorators", e[e.colorDecoratorsLimit = 27] = "colorDecoratorsLimit", e[e.columnSelection = 28] = "columnSelection", e[e.comments = 29] = "comments", e[e.contextmenu = 30] = "contextmenu", e[e.copyWithSyntaxHighlighting = 31] = "copyWithSyntaxHighlighting", e[e.cursorBlinking = 32] = "cursorBlinking", e[e.cursorSmoothCaretAnimation = 33] = "cursorSmoothCaretAnimation", e[e.cursorStyle = 34] = "cursorStyle", e[e.cursorSurroundingLines = 35] = "cursorSurroundingLines", e[e.cursorSurroundingLinesStyle = 36] = "cursorSurroundingLinesStyle", e[e.cursorWidth = 37] = "cursorWidth", e[e.cursorHeight = 38] = "cursorHeight", e[e.disableLayerHinting = 39] = "disableLayerHinting", e[e.disableMonospaceOptimizations = 40] = "disableMonospaceOptimizations", e[e.domReadOnly = 41] = "domReadOnly", e[e.dragAndDrop = 42] = "dragAndDrop", e[e.dropIntoEditor = 43] = "dropIntoEditor", e[e.editContext = 44] = "editContext", e[e.emptySelectionClipboard = 45] = "emptySelectionClipboard", e[e.experimentalGpuAcceleration = 46] = "experimentalGpuAcceleration", e[e.experimentalWhitespaceRendering = 47] = "experimentalWhitespaceRendering", e[e.extraEditorClassName = 48] = "extraEditorClassName", e[e.fastScrollSensitivity = 49] = "fastScrollSensitivity", e[e.find = 50] = "find", e[e.fixedOverflowWidgets = 51] = "fixedOverflowWidgets", e[e.folding = 52] = "folding", e[e.foldingStrategy = 53] = "foldingStrategy", e[e.foldingHighlight = 54] = "foldingHighlight", e[e.foldingImportsByDefault = 55] = "foldingImportsByDefault", e[e.foldingMaximumRegions = 56] = "foldingMaximumRegions", e[e.unfoldOnClickAfterEndOfLine = 57] = "unfoldOnClickAfterEndOfLine", e[e.fontFamily = 58] = "fontFamily", e[e.fontInfo = 59] = "fontInfo", e[e.fontLigatures = 60] = "fontLigatures", e[e.fontSize = 61] = "fontSize", e[e.fontWeight = 62] = "fontWeight", e[e.fontVariations = 63] = "fontVariations", e[e.formatOnPaste = 64] = "formatOnPaste", e[e.formatOnType = 65] = "formatOnType", e[e.glyphMargin = 66] = "glyphMargin", e[e.gotoLocation = 67] = "gotoLocation", e[e.hideCursorInOverviewRuler = 68] = "hideCursorInOverviewRuler", e[e.hover = 69] = "hover", e[e.inDiffEditor = 70] = "inDiffEditor", e[e.inlineSuggest = 71] = "inlineSuggest", e[e.letterSpacing = 72] = "letterSpacing", e[e.lightbulb = 73] = "lightbulb", e[e.lineDecorationsWidth = 74] = "lineDecorationsWidth", e[e.lineHeight = 75] = "lineHeight", e[e.lineNumbers = 76] = "lineNumbers", e[e.lineNumbersMinChars = 77] = "lineNumbersMinChars", e[e.linkedEditing = 78] = "linkedEditing", e[e.links = 79] = "links", e[e.matchBrackets = 80] = "matchBrackets", e[e.minimap = 81] = "minimap", e[e.mouseStyle = 82] = "mouseStyle", e[e.mouseWheelScrollSensitivity = 83] = "mouseWheelScrollSensitivity", e[e.mouseWheelZoom = 84] = "mouseWheelZoom", e[e.multiCursorMergeOverlapping = 85] = "multiCursorMergeOverlapping", e[e.multiCursorModifier = 86] = "multiCursorModifier", e[e.mouseMiddleClickAction = 87] = "mouseMiddleClickAction", e[e.multiCursorPaste = 88] = "multiCursorPaste", e[e.multiCursorLimit = 89] = "multiCursorLimit", e[e.occurrencesHighlight = 90] = "occurrencesHighlight", e[e.occurrencesHighlightDelay = 91] = "occurrencesHighlightDelay", e[e.overtypeCursorStyle = 92] = "overtypeCursorStyle", e[e.overtypeOnPaste = 93] = "overtypeOnPaste", e[e.overviewRulerBorder = 94] = "overviewRulerBorder", e[e.overviewRulerLanes = 95] = "overviewRulerLanes", e[e.padding = 96] = "padding", e[e.pasteAs = 97] = "pasteAs", e[e.parameterHints = 98] = "parameterHints", e[e.peekWidgetDefaultFocus = 99] = "peekWidgetDefaultFocus", e[e.placeholder = 100] = "placeholder", e[e.definitionLinkOpensInPeek = 101] = "definitionLinkOpensInPeek", e[e.quickSuggestions = 102] = "quickSuggestions", e[e.quickSuggestionsDelay = 103] = "quickSuggestionsDelay", e[e.readOnly = 104] = "readOnly", e[e.readOnlyMessage = 105] = "readOnlyMessage", e[e.renameOnType = 106] = "renameOnType", e[e.renderRichScreenReaderContent = 107] = "renderRichScreenReaderContent", e[e.renderControlCharacters = 108] = "renderControlCharacters", e[e.renderFinalNewline = 109] = "renderFinalNewline", e[e.renderLineHighlight = 110] = "renderLineHighlight", e[e.renderLineHighlightOnlyWhenFocus = 111] = "renderLineHighlightOnlyWhenFocus", e[e.renderValidationDecorations = 112] = "renderValidationDecorations", e[e.renderWhitespace = 113] = "renderWhitespace", e[e.revealHorizontalRightPadding = 114] = "revealHorizontalRightPadding", e[e.roundedSelection = 115] = "roundedSelection", e[e.rulers = 116] = "rulers", e[e.scrollbar = 117] = "scrollbar", e[e.scrollBeyondLastColumn = 118] = "scrollBeyondLastColumn", e[e.scrollBeyondLastLine = 119] = "scrollBeyondLastLine", e[e.scrollPredominantAxis = 120] = "scrollPredominantAxis", e[e.selectionClipboard = 121] = "selectionClipboard", e[e.selectionHighlight = 122] = "selectionHighlight", e[e.selectionHighlightMaxLength = 123] = "selectionHighlightMaxLength", e[e.selectionHighlightMultiline = 124] = "selectionHighlightMultiline", e[e.selectOnLineNumbers = 125] = "selectOnLineNumbers", e[e.showFoldingControls = 126] = "showFoldingControls", e[e.showUnused = 127] = "showUnused", e[e.snippetSuggestions = 128] = "snippetSuggestions", e[e.smartSelect = 129] = "smartSelect", e[e.smoothScrolling = 130] = "smoothScrolling", e[e.stickyScroll = 131] = "stickyScroll", e[e.stickyTabStops = 132] = "stickyTabStops", e[e.stopRenderingLineAfter = 133] = "stopRenderingLineAfter", e[e.suggest = 134] = "suggest", e[e.suggestFontSize = 135] = "suggestFontSize", e[e.suggestLineHeight = 136] = "suggestLineHeight", e[e.suggestOnTriggerCharacters = 137] = "suggestOnTriggerCharacters", e[e.suggestSelection = 138] = "suggestSelection", e[e.tabCompletion = 139] = "tabCompletion", e[e.tabIndex = 140] = "tabIndex", e[e.trimWhitespaceOnDelete = 141] = "trimWhitespaceOnDelete", e[e.unicodeHighlighting = 142] = "unicodeHighlighting", e[e.unusualLineTerminators = 143] = "unusualLineTerminators", e[e.useShadowDOM = 144] = "useShadowDOM", e[e.useTabStops = 145] = "useTabStops", e[e.wordBreak = 146] = "wordBreak", e[e.wordSegmenterLocales = 147] = "wordSegmenterLocales", e[e.wordSeparators = 148] = "wordSeparators", e[e.wordWrap = 149] = "wordWrap", e[e.wordWrapBreakAfterCharacters = 150] = "wordWrapBreakAfterCharacters", e[e.wordWrapBreakBeforeCharacters = 151] = "wordWrapBreakBeforeCharacters", e[e.wordWrapColumn = 152] = "wordWrapColumn", e[e.wordWrapOverride1 = 153] = "wordWrapOverride1", e[e.wordWrapOverride2 = 154] = "wordWrapOverride2", e[e.wrappingIndent = 155] = "wrappingIndent", e[e.wrappingStrategy = 156] = "wrappingStrategy", e[e.showDeprecated = 157] = "showDeprecated", e[e.inertialScroll = 158] = "inertialScroll", e[e.inlayHints = 159] = "inlayHints", e[e.wrapOnEscapedLineFeeds = 160] = "wrapOnEscapedLineFeeds", e[e.effectiveCursorStyle = 161] = "effectiveCursorStyle", e[e.editorClassName = 162] = "editorClassName", e[e.pixelRatio = 163] = "pixelRatio", e[e.tabFocusMode = 164] = "tabFocusMode", e[e.layoutInfo = 165] = "layoutInfo", e[e.wrappingInfo = 166] = "wrappingInfo", e[e.defaultColorDecorators = 167] = "defaultColorDecorators", e[e.colorDecoratorsActivatedOn = 168] = "colorDecoratorsActivatedOn", e[e.inlineCompletionsAccessibilityVerbose = 169] = "inlineCompletionsAccessibilityVerbose", e[e.effectiveEditContext = 170] = "effectiveEditContext", e[e.scrollOnMiddleClick = 171] = "scrollOnMiddleClick", e[e.effectiveAllowVariableFonts = 172] = "effectiveAllowVariableFonts";
})(Pc || (Pc = {}));
var Ic;
(function(e) {
  e[e.TextDefined = 0] = "TextDefined", e[e.LF = 1] = "LF", e[e.CRLF = 2] = "CRLF";
})(Ic || (Ic = {}));
var $c;
(function(e) {
  e[e.LF = 0] = "LF", e[e.CRLF = 1] = "CRLF";
})($c || ($c = {}));
var Bc;
(function(e) {
  e[e.Left = 1] = "Left", e[e.Center = 2] = "Center", e[e.Right = 3] = "Right";
})(Bc || (Bc = {}));
var Vc;
(function(e) {
  e[e.Increase = 0] = "Increase", e[e.Decrease = 1] = "Decrease";
})(Vc || (Vc = {}));
var jc;
(function(e) {
  e[e.None = 0] = "None", e[e.Indent = 1] = "Indent", e[e.IndentOutdent = 2] = "IndentOutdent", e[e.Outdent = 3] = "Outdent";
})(jc || (jc = {}));
var Uc;
(function(e) {
  e[e.Both = 0] = "Both", e[e.Right = 1] = "Right", e[e.Left = 2] = "Left", e[e.None = 3] = "None";
})(Uc || (Uc = {}));
var qc;
(function(e) {
  e[e.Type = 1] = "Type", e[e.Parameter = 2] = "Parameter";
})(qc || (qc = {}));
var Wc;
(function(e) {
  e[e.Code = 1] = "Code", e[e.Label = 2] = "Label";
})(Wc || (Wc = {}));
var Hc;
(function(e) {
  e[e.Accepted = 0] = "Accepted", e[e.Rejected = 1] = "Rejected", e[e.Ignored = 2] = "Ignored";
})(Hc || (Hc = {}));
var Yc;
(function(e) {
  e[e.Automatic = 0] = "Automatic", e[e.Explicit = 1] = "Explicit";
})(Yc || (Yc = {}));
var Vo;
(function(e) {
  e[e.DependsOnKbLayout = -1] = "DependsOnKbLayout", e[e.Unknown = 0] = "Unknown", e[e.Backspace = 1] = "Backspace", e[e.Tab = 2] = "Tab", e[e.Enter = 3] = "Enter", e[e.Shift = 4] = "Shift", e[e.Ctrl = 5] = "Ctrl", e[e.Alt = 6] = "Alt", e[e.PauseBreak = 7] = "PauseBreak", e[e.CapsLock = 8] = "CapsLock", e[e.Escape = 9] = "Escape", e[e.Space = 10] = "Space", e[e.PageUp = 11] = "PageUp", e[e.PageDown = 12] = "PageDown", e[e.End = 13] = "End", e[e.Home = 14] = "Home", e[e.LeftArrow = 15] = "LeftArrow", e[e.UpArrow = 16] = "UpArrow", e[e.RightArrow = 17] = "RightArrow", e[e.DownArrow = 18] = "DownArrow", e[e.Insert = 19] = "Insert", e[e.Delete = 20] = "Delete", e[e.Digit0 = 21] = "Digit0", e[e.Digit1 = 22] = "Digit1", e[e.Digit2 = 23] = "Digit2", e[e.Digit3 = 24] = "Digit3", e[e.Digit4 = 25] = "Digit4", e[e.Digit5 = 26] = "Digit5", e[e.Digit6 = 27] = "Digit6", e[e.Digit7 = 28] = "Digit7", e[e.Digit8 = 29] = "Digit8", e[e.Digit9 = 30] = "Digit9", e[e.KeyA = 31] = "KeyA", e[e.KeyB = 32] = "KeyB", e[e.KeyC = 33] = "KeyC", e[e.KeyD = 34] = "KeyD", e[e.KeyE = 35] = "KeyE", e[e.KeyF = 36] = "KeyF", e[e.KeyG = 37] = "KeyG", e[e.KeyH = 38] = "KeyH", e[e.KeyI = 39] = "KeyI", e[e.KeyJ = 40] = "KeyJ", e[e.KeyK = 41] = "KeyK", e[e.KeyL = 42] = "KeyL", e[e.KeyM = 43] = "KeyM", e[e.KeyN = 44] = "KeyN", e[e.KeyO = 45] = "KeyO", e[e.KeyP = 46] = "KeyP", e[e.KeyQ = 47] = "KeyQ", e[e.KeyR = 48] = "KeyR", e[e.KeyS = 49] = "KeyS", e[e.KeyT = 50] = "KeyT", e[e.KeyU = 51] = "KeyU", e[e.KeyV = 52] = "KeyV", e[e.KeyW = 53] = "KeyW", e[e.KeyX = 54] = "KeyX", e[e.KeyY = 55] = "KeyY", e[e.KeyZ = 56] = "KeyZ", e[e.Meta = 57] = "Meta", e[e.ContextMenu = 58] = "ContextMenu", e[e.F1 = 59] = "F1", e[e.F2 = 60] = "F2", e[e.F3 = 61] = "F3", e[e.F4 = 62] = "F4", e[e.F5 = 63] = "F5", e[e.F6 = 64] = "F6", e[e.F7 = 65] = "F7", e[e.F8 = 66] = "F8", e[e.F9 = 67] = "F9", e[e.F10 = 68] = "F10", e[e.F11 = 69] = "F11", e[e.F12 = 70] = "F12", e[e.F13 = 71] = "F13", e[e.F14 = 72] = "F14", e[e.F15 = 73] = "F15", e[e.F16 = 74] = "F16", e[e.F17 = 75] = "F17", e[e.F18 = 76] = "F18", e[e.F19 = 77] = "F19", e[e.F20 = 78] = "F20", e[e.F21 = 79] = "F21", e[e.F22 = 80] = "F22", e[e.F23 = 81] = "F23", e[e.F24 = 82] = "F24", e[e.NumLock = 83] = "NumLock", e[e.ScrollLock = 84] = "ScrollLock", e[e.Semicolon = 85] = "Semicolon", e[e.Equal = 86] = "Equal", e[e.Comma = 87] = "Comma", e[e.Minus = 88] = "Minus", e[e.Period = 89] = "Period", e[e.Slash = 90] = "Slash", e[e.Backquote = 91] = "Backquote", e[e.BracketLeft = 92] = "BracketLeft", e[e.Backslash = 93] = "Backslash", e[e.BracketRight = 94] = "BracketRight", e[e.Quote = 95] = "Quote", e[e.OEM_8 = 96] = "OEM_8", e[e.IntlBackslash = 97] = "IntlBackslash", e[e.Numpad0 = 98] = "Numpad0", e[e.Numpad1 = 99] = "Numpad1", e[e.Numpad2 = 100] = "Numpad2", e[e.Numpad3 = 101] = "Numpad3", e[e.Numpad4 = 102] = "Numpad4", e[e.Numpad5 = 103] = "Numpad5", e[e.Numpad6 = 104] = "Numpad6", e[e.Numpad7 = 105] = "Numpad7", e[e.Numpad8 = 106] = "Numpad8", e[e.Numpad9 = 107] = "Numpad9", e[e.NumpadMultiply = 108] = "NumpadMultiply", e[e.NumpadAdd = 109] = "NumpadAdd", e[e.NUMPAD_SEPARATOR = 110] = "NUMPAD_SEPARATOR", e[e.NumpadSubtract = 111] = "NumpadSubtract", e[e.NumpadDecimal = 112] = "NumpadDecimal", e[e.NumpadDivide = 113] = "NumpadDivide", e[e.KEY_IN_COMPOSITION = 114] = "KEY_IN_COMPOSITION", e[e.ABNT_C1 = 115] = "ABNT_C1", e[e.ABNT_C2 = 116] = "ABNT_C2", e[e.AudioVolumeMute = 117] = "AudioVolumeMute", e[e.AudioVolumeUp = 118] = "AudioVolumeUp", e[e.AudioVolumeDown = 119] = "AudioVolumeDown", e[e.BrowserSearch = 120] = "BrowserSearch", e[e.BrowserHome = 121] = "BrowserHome", e[e.BrowserBack = 122] = "BrowserBack", e[e.BrowserForward = 123] = "BrowserForward", e[e.MediaTrackNext = 124] = "MediaTrackNext", e[e.MediaTrackPrevious = 125] = "MediaTrackPrevious", e[e.MediaStop = 126] = "MediaStop", e[e.MediaPlayPause = 127] = "MediaPlayPause", e[e.LaunchMediaPlayer = 128] = "LaunchMediaPlayer", e[e.LaunchMail = 129] = "LaunchMail", e[e.LaunchApp2 = 130] = "LaunchApp2", e[e.Clear = 131] = "Clear", e[e.MAX_VALUE = 132] = "MAX_VALUE";
})(Vo || (Vo = {}));
var jo;
(function(e) {
  e[e.Hint = 1] = "Hint", e[e.Info = 2] = "Info", e[e.Warning = 4] = "Warning", e[e.Error = 8] = "Error";
})(jo || (jo = {}));
var Uo;
(function(e) {
  e[e.Unnecessary = 1] = "Unnecessary", e[e.Deprecated = 2] = "Deprecated";
})(Uo || (Uo = {}));
var zc;
(function(e) {
  e[e.Inline = 1] = "Inline", e[e.Gutter = 2] = "Gutter";
})(zc || (zc = {}));
var Gc;
(function(e) {
  e[e.Normal = 1] = "Normal", e[e.Underlined = 2] = "Underlined";
})(Gc || (Gc = {}));
var Jc;
(function(e) {
  e[e.UNKNOWN = 0] = "UNKNOWN", e[e.TEXTAREA = 1] = "TEXTAREA", e[e.GUTTER_GLYPH_MARGIN = 2] = "GUTTER_GLYPH_MARGIN", e[e.GUTTER_LINE_NUMBERS = 3] = "GUTTER_LINE_NUMBERS", e[e.GUTTER_LINE_DECORATIONS = 4] = "GUTTER_LINE_DECORATIONS", e[e.GUTTER_VIEW_ZONE = 5] = "GUTTER_VIEW_ZONE", e[e.CONTENT_TEXT = 6] = "CONTENT_TEXT", e[e.CONTENT_EMPTY = 7] = "CONTENT_EMPTY", e[e.CONTENT_VIEW_ZONE = 8] = "CONTENT_VIEW_ZONE", e[e.CONTENT_WIDGET = 9] = "CONTENT_WIDGET", e[e.OVERVIEW_RULER = 10] = "OVERVIEW_RULER", e[e.SCROLLBAR = 11] = "SCROLLBAR", e[e.OVERLAY_WIDGET = 12] = "OVERLAY_WIDGET", e[e.OUTSIDE_EDITOR = 13] = "OUTSIDE_EDITOR";
})(Jc || (Jc = {}));
var Qc;
(function(e) {
  e[e.AIGenerated = 1] = "AIGenerated";
})(Qc || (Qc = {}));
var Kc;
(function(e) {
  e[e.Invoke = 0] = "Invoke", e[e.Automatic = 1] = "Automatic";
})(Kc || (Kc = {}));
var Xc;
(function(e) {
  e[e.TOP_RIGHT_CORNER = 0] = "TOP_RIGHT_CORNER", e[e.BOTTOM_RIGHT_CORNER = 1] = "BOTTOM_RIGHT_CORNER", e[e.TOP_CENTER = 2] = "TOP_CENTER";
})(Xc || (Xc = {}));
var Zc;
(function(e) {
  e[e.Left = 1] = "Left", e[e.Center = 2] = "Center", e[e.Right = 4] = "Right", e[e.Full = 7] = "Full";
})(Zc || (Zc = {}));
var ef;
(function(e) {
  e[e.Word = 0] = "Word", e[e.Line = 1] = "Line", e[e.Suggest = 2] = "Suggest";
})(ef || (ef = {}));
var tf;
(function(e) {
  e[e.Left = 0] = "Left", e[e.Right = 1] = "Right", e[e.None = 2] = "None", e[e.LeftOfInjectedText = 3] = "LeftOfInjectedText", e[e.RightOfInjectedText = 4] = "RightOfInjectedText";
})(tf || (tf = {}));
var nf;
(function(e) {
  e[e.Off = 0] = "Off", e[e.On = 1] = "On", e[e.Relative = 2] = "Relative", e[e.Interval = 3] = "Interval", e[e.Custom = 4] = "Custom";
})(nf || (nf = {}));
var rf;
(function(e) {
  e[e.None = 0] = "None", e[e.Text = 1] = "Text", e[e.Blocks = 2] = "Blocks";
})(rf || (rf = {}));
var sf;
(function(e) {
  e[e.Smooth = 0] = "Smooth", e[e.Immediate = 1] = "Immediate";
})(sf || (sf = {}));
var af;
(function(e) {
  e[e.Auto = 1] = "Auto", e[e.Hidden = 2] = "Hidden", e[e.Visible = 3] = "Visible";
})(af || (af = {}));
var qo;
(function(e) {
  e[e.LTR = 0] = "LTR", e[e.RTL = 1] = "RTL";
})(qo || (qo = {}));
var of;
(function(e) {
  e.Off = "off", e.OnCode = "onCode", e.On = "on";
})(of || (of = {}));
var lf;
(function(e) {
  e[e.Invoke = 1] = "Invoke", e[e.TriggerCharacter = 2] = "TriggerCharacter", e[e.ContentChange = 3] = "ContentChange";
})(lf || (lf = {}));
var uf;
(function(e) {
  e[e.File = 0] = "File", e[e.Module = 1] = "Module", e[e.Namespace = 2] = "Namespace", e[e.Package = 3] = "Package", e[e.Class = 4] = "Class", e[e.Method = 5] = "Method", e[e.Property = 6] = "Property", e[e.Field = 7] = "Field", e[e.Constructor = 8] = "Constructor", e[e.Enum = 9] = "Enum", e[e.Interface = 10] = "Interface", e[e.Function = 11] = "Function", e[e.Variable = 12] = "Variable", e[e.Constant = 13] = "Constant", e[e.String = 14] = "String", e[e.Number = 15] = "Number", e[e.Boolean = 16] = "Boolean", e[e.Array = 17] = "Array", e[e.Object = 18] = "Object", e[e.Key = 19] = "Key", e[e.Null = 20] = "Null", e[e.EnumMember = 21] = "EnumMember", e[e.Struct = 22] = "Struct", e[e.Event = 23] = "Event", e[e.Operator = 24] = "Operator", e[e.TypeParameter = 25] = "TypeParameter";
})(uf || (uf = {}));
var cf;
(function(e) {
  e[e.Deprecated = 1] = "Deprecated";
})(cf || (cf = {}));
var ff;
(function(e) {
  e[e.LTR = 0] = "LTR", e[e.RTL = 1] = "RTL";
})(ff || (ff = {}));
var hf;
(function(e) {
  e[e.Hidden = 0] = "Hidden", e[e.Blink = 1] = "Blink", e[e.Smooth = 2] = "Smooth", e[e.Phase = 3] = "Phase", e[e.Expand = 4] = "Expand", e[e.Solid = 5] = "Solid";
})(hf || (hf = {}));
var df;
(function(e) {
  e[e.Line = 1] = "Line", e[e.Block = 2] = "Block", e[e.Underline = 3] = "Underline", e[e.LineThin = 4] = "LineThin", e[e.BlockOutline = 5] = "BlockOutline", e[e.UnderlineThin = 6] = "UnderlineThin";
})(df || (df = {}));
var mf;
(function(e) {
  e[e.AlwaysGrowsWhenTypingAtEdges = 0] = "AlwaysGrowsWhenTypingAtEdges", e[e.NeverGrowsWhenTypingAtEdges = 1] = "NeverGrowsWhenTypingAtEdges", e[e.GrowsOnlyWhenTypingBefore = 2] = "GrowsOnlyWhenTypingBefore", e[e.GrowsOnlyWhenTypingAfter = 3] = "GrowsOnlyWhenTypingAfter";
})(mf || (mf = {}));
var pf;
(function(e) {
  e[e.None = 0] = "None", e[e.Same = 1] = "Same", e[e.Indent = 2] = "Indent", e[e.DeepIndent = 3] = "DeepIndent";
})(pf || (pf = {}));
const jr = class jr {
  static chord(t, n) {
    return T0(t, n);
  }
};
jr.CtrlCmd = 2048, jr.Shift = 1024, jr.Alt = 512, jr.WinCtrl = 256;
let Wo = jr;
function ny() {
  return {
    editor: void 0,
    // undefined override expected here
    languages: void 0,
    // undefined override expected here
    CancellationTokenSource: k0,
    Emitter: Ht,
    KeyCode: Vo,
    KeyMod: Wo,
    Position: Ne,
    Range: fe,
    Selection: dt,
    SelectionDirection: qo,
    MarkerSeverity: jo,
    MarkerTag: Uo,
    Uri: su,
    Token: ty
  };
}
var gf;
class ry {
  constructor() {
    this[gf] = "LinkedMap", this._map = /* @__PURE__ */ new Map(), this._head = void 0, this._tail = void 0, this._size = 0, this._state = 0;
  }
  clear() {
    this._map.clear(), this._head = void 0, this._tail = void 0, this._size = 0, this._state++;
  }
  isEmpty() {
    return !this._head && !this._tail;
  }
  get size() {
    return this._size;
  }
  get first() {
    return this._head?.value;
  }
  get last() {
    return this._tail?.value;
  }
  has(t) {
    return this._map.has(t);
  }
  get(t, n = 0) {
    const r = this._map.get(t);
    if (r)
      return n !== 0 && this.touch(r, n), r.value;
  }
  set(t, n, r = 0) {
    let s = this._map.get(t);
    if (s)
      s.value = n, r !== 0 && this.touch(s, r);
    else {
      switch (s = { key: t, value: n, next: void 0, previous: void 0 }, r) {
        case 0:
          this.addItemLast(s);
          break;
        case 1:
          this.addItemFirst(s);
          break;
        case 2:
          this.addItemLast(s);
          break;
        default:
          this.addItemLast(s);
          break;
      }
      this._map.set(t, s), this._size++;
    }
    return this;
  }
  delete(t) {
    return !!this.remove(t);
  }
  remove(t) {
    const n = this._map.get(t);
    if (n)
      return this._map.delete(t), this.removeItem(n), this._size--, n.value;
  }
  shift() {
    if (!this._head && !this._tail)
      return;
    if (!this._head || !this._tail)
      throw new Error("Invalid list");
    const t = this._head;
    return this._map.delete(t.key), this.removeItem(t), this._size--, t.value;
  }
  forEach(t, n) {
    const r = this._state;
    let s = this._head;
    for (; s; ) {
      if (n ? t.bind(n)(s.value, s.key, this) : t(s.value, s.key, this), this._state !== r)
        throw new Error("LinkedMap got modified during iteration.");
      s = s.next;
    }
  }
  keys() {
    const t = this, n = this._state;
    let r = this._head;
    const s = {
      [Symbol.iterator]() {
        return s;
      },
      next() {
        if (t._state !== n)
          throw new Error("LinkedMap got modified during iteration.");
        if (r) {
          const i = { value: r.key, done: !1 };
          return r = r.next, i;
        } else
          return { value: void 0, done: !0 };
      }
    };
    return s;
  }
  values() {
    const t = this, n = this._state;
    let r = this._head;
    const s = {
      [Symbol.iterator]() {
        return s;
      },
      next() {
        if (t._state !== n)
          throw new Error("LinkedMap got modified during iteration.");
        if (r) {
          const i = { value: r.value, done: !1 };
          return r = r.next, i;
        } else
          return { value: void 0, done: !0 };
      }
    };
    return s;
  }
  entries() {
    const t = this, n = this._state;
    let r = this._head;
    const s = {
      [Symbol.iterator]() {
        return s;
      },
      next() {
        if (t._state !== n)
          throw new Error("LinkedMap got modified during iteration.");
        if (r) {
          const i = { value: [r.key, r.value], done: !1 };
          return r = r.next, i;
        } else
          return { value: void 0, done: !0 };
      }
    };
    return s;
  }
  [(gf = Symbol.toStringTag, Symbol.iterator)]() {
    return this.entries();
  }
  trimOld(t) {
    if (t >= this.size)
      return;
    if (t === 0) {
      this.clear();
      return;
    }
    let n = this._head, r = this.size;
    for (; n && r > t; )
      this._map.delete(n.key), n = n.next, r--;
    this._head = n, this._size = r, n && (n.previous = void 0), this._state++;
  }
  trimNew(t) {
    if (t >= this.size)
      return;
    if (t === 0) {
      this.clear();
      return;
    }
    let n = this._tail, r = this.size;
    for (; n && r > t; )
      this._map.delete(n.key), n = n.previous, r--;
    this._tail = n, this._size = r, n && (n.next = void 0), this._state++;
  }
  addItemFirst(t) {
    if (!this._head && !this._tail)
      this._tail = t;
    else if (this._head)
      t.next = this._head, this._head.previous = t;
    else
      throw new Error("Invalid list");
    this._head = t, this._state++;
  }
  addItemLast(t) {
    if (!this._head && !this._tail)
      this._head = t;
    else if (this._tail)
      t.previous = this._tail, this._tail.next = t;
    else
      throw new Error("Invalid list");
    this._tail = t, this._state++;
  }
  removeItem(t) {
    if (t === this._head && t === this._tail)
      this._head = void 0, this._tail = void 0;
    else if (t === this._head) {
      if (!t.next)
        throw new Error("Invalid list");
      t.next.previous = void 0, this._head = t.next;
    } else if (t === this._tail) {
      if (!t.previous)
        throw new Error("Invalid list");
      t.previous.next = void 0, this._tail = t.previous;
    } else {
      const n = t.next, r = t.previous;
      if (!n || !r)
        throw new Error("Invalid list");
      n.previous = r, r.next = n;
    }
    t.next = void 0, t.previous = void 0, this._state++;
  }
  touch(t, n) {
    if (!this._head || !this._tail)
      throw new Error("Invalid list");
    if (!(n !== 1 && n !== 2)) {
      if (n === 1) {
        if (t === this._head)
          return;
        const r = t.next, s = t.previous;
        t === this._tail ? (s.next = void 0, this._tail = s) : (r.previous = s, s.next = r), t.previous = void 0, t.next = this._head, this._head.previous = t, this._head = t, this._state++;
      } else if (n === 2) {
        if (t === this._tail)
          return;
        const r = t.next, s = t.previous;
        t === this._head ? (r.previous = void 0, this._head = r) : (r.previous = s, s.next = r), t.next = void 0, t.previous = this._tail, this._tail.next = t, this._tail = t, this._state++;
      }
    }
  }
  toJSON() {
    const t = [];
    return this.forEach((n, r) => {
      t.push([r, n]);
    }), t;
  }
  fromJSON(t) {
    this.clear();
    for (const [n, r] of t)
      this.set(n, r);
  }
}
class sy extends ry {
  constructor(t, n = 1) {
    super(), this._limit = t, this._ratio = Math.min(Math.max(0, n), 1);
  }
  get limit() {
    return this._limit;
  }
  set limit(t) {
    this._limit = t, this.checkTrim();
  }
  get(t, n = 2) {
    return super.get(t, n);
  }
  peek(t) {
    return super.get(
      t,
      0
      /* Touch.None */
    );
  }
  set(t, n) {
    return super.set(
      t,
      n,
      2
      /* Touch.AsNew */
    ), this;
  }
  checkTrim() {
    this.size > this._limit && this.trim(Math.round(this._limit * this._ratio));
  }
}
class iy extends sy {
  constructor(t, n = 1) {
    super(t, n);
  }
  trim(t) {
    this.trimOld(t);
  }
  set(t, n) {
    return super.set(t, n), this.checkTrim(), this;
  }
}
class ay {
  constructor() {
    this.map = /* @__PURE__ */ new Map();
  }
  add(t, n) {
    let r = this.map.get(t);
    r || (r = /* @__PURE__ */ new Set(), this.map.set(t, r)), r.add(n);
  }
  delete(t, n) {
    const r = this.map.get(t);
    r && (r.delete(n), r.size === 0 && this.map.delete(t));
  }
  forEach(t, n) {
    const r = this.map.get(t);
    r && r.forEach(n);
  }
}
new iy(10);
var yf;
(function(e) {
  e[e.Left = 1] = "Left", e[e.Center = 2] = "Center", e[e.Right = 4] = "Right", e[e.Full = 7] = "Full";
})(yf || (yf = {}));
var bf;
(function(e) {
  e[e.Left = 1] = "Left", e[e.Center = 2] = "Center", e[e.Right = 3] = "Right";
})(bf || (bf = {}));
var vf;
(function(e) {
  e[e.LTR = 0] = "LTR", e[e.RTL = 1] = "RTL";
})(vf || (vf = {}));
var wf;
(function(e) {
  e[e.Both = 0] = "Both", e[e.Right = 1] = "Right", e[e.Left = 2] = "Left", e[e.None = 3] = "None";
})(wf || (wf = {}));
function oy(e) {
  if (!e || e.length === 0)
    return !1;
  for (let t = 0, n = e.length; t < n; t++) {
    const r = e.charCodeAt(t);
    if (r === 10)
      return !0;
    if (r === 92) {
      if (t++, t >= n)
        break;
      const s = e.charCodeAt(t);
      if (s === 110 || s === 114 || s === 87)
        return !0;
    }
  }
  return !1;
}
function ly(e, t, n, r, s) {
  if (r === 0)
    return !0;
  const i = t.charCodeAt(r - 1);
  if (e.get(i) !== 0 || i === 13 || i === 10)
    return !0;
  if (s > 0) {
    const a = t.charCodeAt(r);
    if (e.get(a) !== 0)
      return !0;
  }
  return !1;
}
function uy(e, t, n, r, s) {
  if (r + s === n)
    return !0;
  const i = t.charCodeAt(r + s);
  if (e.get(i) !== 0 || i === 13 || i === 10)
    return !0;
  if (s > 0) {
    const a = t.charCodeAt(r + s - 1);
    if (e.get(a) !== 0)
      return !0;
  }
  return !1;
}
function cy(e, t, n, r, s) {
  return ly(e, t, n, r, s) && uy(e, t, n, r, s);
}
class fy {
  constructor(t, n) {
    this._wordSeparators = t, this._searchRegex = n, this._prevMatchStartIndex = -1, this._prevMatchLength = 0;
  }
  reset(t) {
    this._searchRegex.lastIndex = t, this._prevMatchStartIndex = -1, this._prevMatchLength = 0;
  }
  next(t) {
    const n = t.length;
    let r;
    do {
      if (this._prevMatchStartIndex + this._prevMatchLength === n || (r = this._searchRegex.exec(t), !r))
        return null;
      const s = r.index, i = r[0].length;
      if (s === this._prevMatchStartIndex && i === this._prevMatchLength) {
        if (i === 0) {
          c0(t, n, this._searchRegex.lastIndex) > 65535 ? this._searchRegex.lastIndex += 2 : this._searchRegex.lastIndex += 1;
          continue;
        }
        return null;
      }
      if (this._prevMatchStartIndex = s, this._prevMatchLength = i, !this._wordSeparators || cy(this._wordSeparators, t, n, s, i))
        return r;
    } while (r);
    return null;
  }
}
const hy = "`~!@#$%^&*()-=+[{]}\\|;:'\",.<>/?";
function dy(e = "") {
  let t = "(-?\\d*\\.\\d\\w*)|([^";
  for (const n of hy)
    e.indexOf(n) >= 0 || (t += "\\" + n);
  return t += "\\s]+)", new RegExp(t, "g");
}
const m1 = dy();
function p1(e) {
  let t = m1;
  if (e && e instanceof RegExp)
    if (e.global)
      t = e;
    else {
      let n = "g";
      e.ignoreCase && (n += "i"), e.multiline && (n += "m"), e.unicode && (n += "u"), t = new RegExp(e.source, n);
    }
  return t.lastIndex = 0, t;
}
const g1 = new Ig();
g1.unshift({
  maxLen: 1e3,
  windowSize: 15,
  timeBudget: 150
});
function iu(e, t, n, r, s) {
  if (t = p1(t), s || (s = Hi.first(g1)), n.length > s.maxLen) {
    let u = e - s.maxLen / 2;
    return u < 0 ? u = 0 : r += u, n = n.substring(u, e + s.maxLen / 2), iu(e, t, n, r, s);
  }
  const i = Date.now(), a = e - 1 - r;
  let o = -1, l = null;
  for (let u = 1; !(Date.now() - i >= s.timeBudget); u++) {
    const f = a - s.windowSize * u;
    t.lastIndex = Math.max(0, f);
    const c = my(t, n, a, o);
    if (!c && l || (l = c, f <= 0))
      break;
    o = f;
  }
  if (l) {
    const u = {
      word: l[0],
      startColumn: r + 1 + l.index,
      endColumn: r + 1 + l.index + l[0].length
    };
    return t.lastIndex = 0, u;
  }
  return null;
}
function my(e, t, n, r) {
  let s;
  for (; s = e.exec(t); ) {
    const i = s.index || 0;
    if (i <= n && e.lastIndex >= n)
      return s;
    if (r > 0 && i > r)
      return null;
  }
  return null;
}
class py {
  static computeUnicodeHighlights(t, n, r) {
    const s = r ? r.startLineNumber : 1, i = r ? r.endLineNumber : t.getLineCount(), a = new Df(n), o = a.getCandidateCodePoints();
    let l;
    o === "allNonBasicAscii" ? l = new RegExp("[^\\t\\n\\r\\x20-\\x7E]", "g") : l = new RegExp(`${gy(Array.from(o))}`, "g");
    const u = new fy(null, l), f = [];
    let c = !1, d, v = 0, D = 0, S = 0;
    e: for (let x = s, N = i; x <= N; x++) {
      const k = t.getLineContent(x), y = k.length;
      u.reset(0);
      do
        if (d = u.next(k), d) {
          let b = d.index, h = d.index + d[0].length;
          if (b > 0) {
            const w = k.charCodeAt(b - 1);
            Mo(w) && b--;
          }
          if (h + 1 < y) {
            const w = k.charCodeAt(h - 1);
            Mo(w) && h++;
          }
          const m = k.substring(b, h);
          let p = iu(b + 1, m1, k, 0);
          p && p.endColumn <= b + 1 && (p = null);
          const E = a.shouldHighlightNonBasicASCII(m, p ? p.word : null);
          if (E !== 0) {
            if (E === 3 ? v++ : E === 2 ? D++ : E === 1 ? S++ : _g(), f.length >= 1e3) {
              c = !0;
              break e;
            }
            f.push(new fe(x, b + 1, x, h + 1));
          }
        }
      while (d);
    }
    return {
      ranges: f,
      hasMore: c,
      ambiguousCharacterCount: v,
      invisibleCharacterCount: D,
      nonBasicAsciiCharacterCount: S
    };
  }
  static computeUnicodeHighlightReason(t, n) {
    const r = new Df(n);
    switch (r.shouldHighlightNonBasicASCII(t, null)) {
      case 0:
        return null;
      case 2:
        return {
          kind: 1
          /* UnicodeHighlighterReasonKind.Invisible */
        };
      case 3: {
        const i = t.codePointAt(0), a = r.ambiguousCharacters.getPrimaryConfusable(i), o = zs.getLocales().filter((l) => !zs.getInstance(/* @__PURE__ */ new Set([...n.allowedLocales, l])).isAmbiguous(i));
        return { kind: 0, confusableWith: String.fromCodePoint(a), notAmbiguousInLocales: o };
      }
      case 1:
        return {
          kind: 2
          /* UnicodeHighlighterReasonKind.NonBasicAscii */
        };
    }
  }
}
function gy(e, t) {
  return `[${t0(e.map((r) => String.fromCodePoint(r)).join(""))}]`;
}
class Df {
  constructor(t) {
    this.options = t, this.allowedCodePoints = new Set(t.allowedCodePoints), this.ambiguousCharacters = zs.getInstance(new Set(t.allowedLocales));
  }
  getCandidateCodePoints() {
    if (this.options.nonBasicASCII)
      return "allNonBasicAscii";
    const t = /* @__PURE__ */ new Set();
    if (this.options.invisibleCharacters)
      for (const n of Fs.codePoints)
        Sf(String.fromCodePoint(n)) || t.add(n);
    if (this.options.ambiguousCharacters)
      for (const n of this.ambiguousCharacters.getConfusableCodePoints())
        t.add(n);
    for (const n of this.allowedCodePoints)
      t.delete(n);
    return t;
  }
  shouldHighlightNonBasicASCII(t, n) {
    const r = t.codePointAt(0);
    if (this.allowedCodePoints.has(r))
      return 0;
    if (this.options.nonBasicASCII)
      return 1;
    let s = !1, i = !1;
    if (n)
      for (const a of n) {
        const o = a.codePointAt(0), l = h0(a);
        s = s || l, !l && !this.ambiguousCharacters.isAmbiguous(o) && !Fs.isInvisibleCharacter(o) && (i = !0);
      }
    return (
      /* Don't allow mixing weird looking characters with ASCII */
      !s && /* Is there an obviously weird looking character? */
      i ? 0 : this.options.invisibleCharacters && !Sf(t) && Fs.isInvisibleCharacter(r) ? 2 : this.options.ambiguousCharacters && this.ambiguousCharacters.isAmbiguous(r) ? 3 : 0
    );
  }
}
function Sf(e) {
  return e === " " || e === `
` || e === "	";
}
class Fi {
  constructor(t, n, r) {
    this.changes = t, this.moves = n, this.hitTimeout = r;
  }
}
class yy {
  constructor(t, n) {
    this.lineRangeMapping = t, this.changes = n;
  }
}
function by(e, t, n = (r, s) => r === s) {
  if (e === t)
    return !0;
  if (!e || !t || e.length !== t.length)
    return !1;
  for (let r = 0, s = e.length; r < s; r++)
    if (!n(e[r], t[r]))
      return !1;
  return !0;
}
function* vy(e, t) {
  let n, r;
  for (const s of e)
    r !== void 0 && t(r, s) ? n.push(s) : (n && (yield n), n = [s]), r = s;
  n && (yield n);
}
function wy(e, t) {
  for (let n = 0; n <= e.length; n++)
    t(n === 0 ? void 0 : e[n - 1], n === e.length ? void 0 : e[n]);
}
function Dy(e, t) {
  for (let n = 0; n < e.length; n++)
    t(n === 0 ? void 0 : e[n - 1], e[n], n + 1 === e.length ? void 0 : e[n + 1]);
}
function Sy(e, t) {
  for (const n of t)
    e.push(n);
}
var Ho;
(function(e) {
  function t(i) {
    return i < 0;
  }
  e.isLessThan = t;
  function n(i) {
    return i <= 0;
  }
  e.isLessThanOrEqual = n;
  function r(i) {
    return i > 0;
  }
  e.isGreaterThan = r;
  function s(i) {
    return i === 0;
  }
  e.isNeitherLessOrGreaterThan = s, e.greaterThan = 1, e.lessThan = -1, e.neitherLessOrGreaterThan = 0;
})(Ho || (Ho = {}));
function _s(e, t) {
  return (n, r) => t(e(n), e(r));
}
const Ts = (e, t) => e - t;
function Ey(e) {
  return (t, n) => -e(t, n);
}
const Ur = class Ur {
  constructor(t) {
    this.iterate = t;
  }
  toArray() {
    const t = [];
    return this.iterate((n) => (t.push(n), !0)), t;
  }
  filter(t) {
    return new Ur((n) => this.iterate((r) => t(r) ? n(r) : !0));
  }
  map(t) {
    return new Ur((n) => this.iterate((r) => n(t(r))));
  }
  findLast(t) {
    let n;
    return this.iterate((r) => (t(r) && (n = r), !0)), n;
  }
  findLastMaxBy(t) {
    let n, r = !0;
    return this.iterate((s) => ((r || Ho.isGreaterThan(t(s, n))) && (r = !1, n = s), !0)), n;
  }
};
Ur.empty = new Ur((t) => {
});
let Ef = Ur;
class he {
  static fromTo(t, n) {
    return new he(t, n);
  }
  static addRange(t, n) {
    let r = 0;
    for (; r < n.length && n[r].endExclusive < t.start; )
      r++;
    let s = r;
    for (; s < n.length && n[s].start <= t.endExclusive; )
      s++;
    if (r === s)
      n.splice(r, 0, t);
    else {
      const i = Math.min(t.start, n[r].start), a = Math.max(t.endExclusive, n[s - 1].endExclusive);
      n.splice(r, s - r, new he(i, a));
    }
  }
  static tryCreate(t, n) {
    if (!(t > n))
      return new he(t, n);
  }
  static ofLength(t) {
    return new he(0, t);
  }
  static ofStartAndLength(t, n) {
    return new he(t, t + n);
  }
  static emptyAt(t) {
    return new he(t, t);
  }
  constructor(t, n) {
    if (this.start = t, this.endExclusive = n, t > n)
      throw new Ge(`Invalid range: ${this.toString()}`);
  }
  get isEmpty() {
    return this.start === this.endExclusive;
  }
  delta(t) {
    return new he(this.start + t, this.endExclusive + t);
  }
  deltaStart(t) {
    return new he(this.start + t, this.endExclusive);
  }
  deltaEnd(t) {
    return new he(this.start, this.endExclusive + t);
  }
  get length() {
    return this.endExclusive - this.start;
  }
  toString() {
    return `[${this.start}, ${this.endExclusive})`;
  }
  equals(t) {
    return this.start === t.start && this.endExclusive === t.endExclusive;
  }
  contains(t) {
    return this.start <= t && t < this.endExclusive;
  }
  /**
   * for all numbers n: range1.contains(n) or range2.contains(n) => range1.join(range2).contains(n)
   * The joined range is the smallest range that contains both ranges.
   */
  join(t) {
    return new he(Math.min(this.start, t.start), Math.max(this.endExclusive, t.endExclusive));
  }
  /**
   * for all numbers n: range1.contains(n) and range2.contains(n) <=> range1.intersect(range2).contains(n)
   *
   * The resulting range is empty if the ranges do not intersect, but touch.
   * If the ranges don't even touch, the result is undefined.
   */
  intersect(t) {
    const n = Math.max(this.start, t.start), r = Math.min(this.endExclusive, t.endExclusive);
    if (n <= r)
      return new he(n, r);
  }
  intersectionLength(t) {
    const n = Math.max(this.start, t.start), r = Math.min(this.endExclusive, t.endExclusive);
    return Math.max(0, r - n);
  }
  intersects(t) {
    const n = Math.max(this.start, t.start), r = Math.min(this.endExclusive, t.endExclusive);
    return n < r;
  }
  intersectsOrTouches(t) {
    const n = Math.max(this.start, t.start), r = Math.min(this.endExclusive, t.endExclusive);
    return n <= r;
  }
  isBefore(t) {
    return this.endExclusive <= t.start;
  }
  isAfter(t) {
    return this.start >= t.endExclusive;
  }
  slice(t) {
    return t.slice(this.start, this.endExclusive);
  }
  substring(t) {
    return t.substring(this.start, this.endExclusive);
  }
  /**
   * Returns the given value if it is contained in this instance, otherwise the closest value that is contained.
   * The range must not be empty.
   */
  clip(t) {
    if (this.isEmpty)
      throw new Ge(`Invalid clipping range: ${this.toString()}`);
    return Math.max(this.start, Math.min(this.endExclusive - 1, t));
  }
  /**
   * Returns `r := value + k * length` such that `r` is contained in this range.
   * The range must not be empty.
   *
   * E.g. `[5, 10).clipCyclic(10) === 5`, `[5, 10).clipCyclic(11) === 6` and `[5, 10).clipCyclic(4) === 9`.
   */
  clipCyclic(t) {
    if (this.isEmpty)
      throw new Ge(`Invalid clipping range: ${this.toString()}`);
    return t < this.start ? this.endExclusive - (this.start - t) % this.length : t >= this.endExclusive ? this.start + (t - this.start) % this.length : t;
  }
  forEach(t) {
    for (let n = this.start; n < this.endExclusive; n++)
      t(n);
  }
  /**
   * this: [ 5, 10), range: [10, 15) => [5, 15)]
   * Throws if the ranges are not touching.
  */
  joinRightTouching(t) {
    if (this.endExclusive !== t.start)
      throw new Ge(`Invalid join: ${this.toString()} and ${t.toString()}`);
    return new he(this.start, t.endExclusive);
  }
}
function Zr(e, t) {
  const n = es(e, t);
  return n === -1 ? void 0 : e[n];
}
function es(e, t, n = 0, r = e.length) {
  let s = n, i = r;
  for (; s < i; ) {
    const a = Math.floor((s + i) / 2);
    t(e[a]) ? s = a + 1 : i = a;
  }
  return s - 1;
}
function Ay(e, t) {
  const n = Yo(e, t);
  return n === e.length ? void 0 : e[n];
}
function Yo(e, t, n = 0, r = e.length) {
  let s = n, i = r;
  for (; s < i; ) {
    const a = Math.floor((s + i) / 2);
    t(e[a]) ? i = a : s = a + 1;
  }
  return s;
}
const Sa = class Sa {
  constructor(t) {
    this._array = t, this._findLastMonotonousLastIdx = 0;
  }
  /**
   * The predicate must be monotonous, i.e. `arr.map(predicate)` must be like `[true, ..., true, false, ..., false]`!
   * For subsequent calls, current predicate must be weaker than (or equal to) the previous predicate, i.e. more entries must be `true`.
   */
  findLastMonotonous(t) {
    if (Sa.assertInvariants) {
      if (this._prevFindLastPredicate) {
        for (const r of this._array)
          if (this._prevFindLastPredicate(r) && !t(r))
            throw new Error("MonotonousArray: current predicate must be weaker than (or equal to) the previous predicate.");
      }
      this._prevFindLastPredicate = t;
    }
    const n = es(this._array, t, this._findLastMonotonousLastIdx);
    return this._findLastMonotonousLastIdx = n + 1, n === -1 ? void 0 : this._array[n];
  }
};
Sa.assertInvariants = !1;
let Ki = Sa;
const mt = class mt {
  static ofLength(t, n) {
    return new mt(t, t + n);
  }
  static fromRange(t) {
    return new mt(t.startLineNumber, t.endLineNumber);
  }
  static fromRangeInclusive(t) {
    return new mt(t.startLineNumber, t.endLineNumber + 1);
  }
  /**
   * @param lineRanges An array of arrays of of sorted line ranges.
   */
  static joinMany(t) {
    if (t.length === 0)
      return [];
    let n = new Yt(t[0].slice());
    for (let r = 1; r < t.length; r++)
      n = n.getUnion(new Yt(t[r].slice()));
    return n.ranges;
  }
  static join(t) {
    if (t.length === 0)
      throw new Ge("lineRanges cannot be empty");
    let n = t[0].startLineNumber, r = t[0].endLineNumberExclusive;
    for (let s = 1; s < t.length; s++)
      n = Math.min(n, t[s].startLineNumber), r = Math.max(r, t[s].endLineNumberExclusive);
    return new mt(n, r);
  }
  /**
   * @internal
   */
  static deserialize(t) {
    return new mt(t[0], t[1]);
  }
  constructor(t, n) {
    if (t > n)
      throw new Ge(`startLineNumber ${t} cannot be after endLineNumberExclusive ${n}`);
    this.startLineNumber = t, this.endLineNumberExclusive = n;
  }
  /**
   * Indicates if this line range contains the given line number.
   */
  contains(t) {
    return this.startLineNumber <= t && t < this.endLineNumberExclusive;
  }
  /**
   * Indicates if this line range is empty.
   */
  get isEmpty() {
    return this.startLineNumber === this.endLineNumberExclusive;
  }
  /**
   * Moves this line range by the given offset of line numbers.
   */
  delta(t) {
    return new mt(this.startLineNumber + t, this.endLineNumberExclusive + t);
  }
  deltaLength(t) {
    return new mt(this.startLineNumber, this.endLineNumberExclusive + t);
  }
  /**
   * The number of lines this line range spans.
   */
  get length() {
    return this.endLineNumberExclusive - this.startLineNumber;
  }
  /**
   * Creates a line range that combines this and the given line range.
   */
  join(t) {
    return new mt(Math.min(this.startLineNumber, t.startLineNumber), Math.max(this.endLineNumberExclusive, t.endLineNumberExclusive));
  }
  toString() {
    return `[${this.startLineNumber},${this.endLineNumberExclusive})`;
  }
  /**
   * The resulting range is empty if the ranges do not intersect, but touch.
   * If the ranges don't even touch, the result is undefined.
   */
  intersect(t) {
    const n = Math.max(this.startLineNumber, t.startLineNumber), r = Math.min(this.endLineNumberExclusive, t.endLineNumberExclusive);
    if (n <= r)
      return new mt(n, r);
  }
  intersectsStrict(t) {
    return this.startLineNumber < t.endLineNumberExclusive && t.startLineNumber < this.endLineNumberExclusive;
  }
  intersectsOrTouches(t) {
    return this.startLineNumber <= t.endLineNumberExclusive && t.startLineNumber <= this.endLineNumberExclusive;
  }
  equals(t) {
    return this.startLineNumber === t.startLineNumber && this.endLineNumberExclusive === t.endLineNumberExclusive;
  }
  toInclusiveRange() {
    return this.isEmpty ? null : new fe(this.startLineNumber, 1, this.endLineNumberExclusive - 1, Number.MAX_SAFE_INTEGER);
  }
  /**
   * @deprecated Using this function is discouraged because it might lead to bugs: The end position is not guaranteed to be a valid position!
  */
  toExclusiveRange() {
    return new fe(this.startLineNumber, 1, this.endLineNumberExclusive, 1);
  }
  mapToLineArray(t) {
    const n = [];
    for (let r = this.startLineNumber; r < this.endLineNumberExclusive; r++)
      n.push(t(r));
    return n;
  }
  forEach(t) {
    for (let n = this.startLineNumber; n < this.endLineNumberExclusive; n++)
      t(n);
  }
  /**
   * @internal
   */
  serialize() {
    return [this.startLineNumber, this.endLineNumberExclusive];
  }
  /**
   * Converts this 1-based line range to a 0-based offset range (subtracts 1!).
   * @internal
   */
  toOffsetRange() {
    return new he(this.startLineNumber - 1, this.endLineNumberExclusive - 1);
  }
  addMargin(t, n) {
    return new mt(this.startLineNumber - t, this.endLineNumberExclusive + n);
  }
};
mt.compareByStart = _s((t) => t.startLineNumber, Ts);
let pe = mt;
class Yt {
  constructor(t = []) {
    this._normalizedRanges = t;
  }
  get ranges() {
    return this._normalizedRanges;
  }
  addRange(t) {
    if (t.length === 0)
      return;
    const n = Yo(this._normalizedRanges, (s) => s.endLineNumberExclusive >= t.startLineNumber), r = es(this._normalizedRanges, (s) => s.startLineNumber <= t.endLineNumberExclusive) + 1;
    if (n === r)
      this._normalizedRanges.splice(n, 0, t);
    else if (n === r - 1) {
      const s = this._normalizedRanges[n];
      this._normalizedRanges[n] = s.join(t);
    } else {
      const s = this._normalizedRanges[n].join(this._normalizedRanges[r - 1]).join(t);
      this._normalizedRanges.splice(n, r - n, s);
    }
  }
  contains(t) {
    const n = Zr(this._normalizedRanges, (r) => r.startLineNumber <= t);
    return !!n && n.endLineNumberExclusive > t;
  }
  intersects(t) {
    const n = Zr(this._normalizedRanges, (r) => r.startLineNumber < t.endLineNumberExclusive);
    return !!n && n.endLineNumberExclusive > t.startLineNumber;
  }
  getUnion(t) {
    if (this._normalizedRanges.length === 0)
      return t;
    if (t._normalizedRanges.length === 0)
      return this;
    const n = [];
    let r = 0, s = 0, i = null;
    for (; r < this._normalizedRanges.length || s < t._normalizedRanges.length; ) {
      let a = null;
      if (r < this._normalizedRanges.length && s < t._normalizedRanges.length) {
        const o = this._normalizedRanges[r], l = t._normalizedRanges[s];
        o.startLineNumber < l.startLineNumber ? (a = o, r++) : (a = l, s++);
      } else r < this._normalizedRanges.length ? (a = this._normalizedRanges[r], r++) : (a = t._normalizedRanges[s], s++);
      i === null ? i = a : i.endLineNumberExclusive >= a.startLineNumber ? i = new pe(i.startLineNumber, Math.max(i.endLineNumberExclusive, a.endLineNumberExclusive)) : (n.push(i), i = a);
    }
    return i !== null && n.push(i), new Yt(n);
  }
  /**
   * Subtracts all ranges in this set from `range` and returns the result.
   */
  subtractFrom(t) {
    const n = Yo(this._normalizedRanges, (a) => a.endLineNumberExclusive >= t.startLineNumber), r = es(this._normalizedRanges, (a) => a.startLineNumber <= t.endLineNumberExclusive) + 1;
    if (n === r)
      return new Yt([t]);
    const s = [];
    let i = t.startLineNumber;
    for (let a = n; a < r; a++) {
      const o = this._normalizedRanges[a];
      o.startLineNumber > i && s.push(new pe(i, o.startLineNumber)), i = o.endLineNumberExclusive;
    }
    return i < t.endLineNumberExclusive && s.push(new pe(i, t.endLineNumberExclusive)), new Yt(s);
  }
  toString() {
    return this._normalizedRanges.map((t) => t.toString()).join(", ");
  }
  getIntersection(t) {
    const n = [];
    let r = 0, s = 0;
    for (; r < this._normalizedRanges.length && s < t._normalizedRanges.length; ) {
      const i = this._normalizedRanges[r], a = t._normalizedRanges[s], o = i.intersect(a);
      o && !o.isEmpty && n.push(o), i.endLineNumberExclusive < a.endLineNumberExclusive ? r++ : s++;
    }
    return new Yt(n);
  }
  getWithDelta(t) {
    return new Yt(this._normalizedRanges.map((n) => n.delta(t)));
  }
}
const Mt = class Mt {
  static betweenPositions(t, n) {
    return t.lineNumber === n.lineNumber ? new Mt(0, n.column - t.column) : new Mt(n.lineNumber - t.lineNumber, n.column - 1);
  }
  static fromPosition(t) {
    return new Mt(t.lineNumber - 1, t.column - 1);
  }
  static ofRange(t) {
    return Mt.betweenPositions(t.getStartPosition(), t.getEndPosition());
  }
  static ofText(t) {
    let n = 0, r = 0;
    for (const s of t)
      s === `
` ? (n++, r = 0) : r++;
    return new Mt(n, r);
  }
  constructor(t, n) {
    this.lineCount = t, this.columnCount = n;
  }
  isGreaterThanOrEqualTo(t) {
    return this.lineCount !== t.lineCount ? this.lineCount > t.lineCount : this.columnCount >= t.columnCount;
  }
  add(t) {
    return t.lineCount === 0 ? new Mt(this.lineCount, this.columnCount + t.columnCount) : new Mt(this.lineCount + t.lineCount, t.columnCount);
  }
  createRange(t) {
    return this.lineCount === 0 ? new fe(t.lineNumber, t.column, t.lineNumber, t.column + this.columnCount) : new fe(t.lineNumber, t.column, t.lineNumber + this.lineCount, this.columnCount + 1);
  }
  toRange() {
    return new fe(1, 1, this.lineCount + 1, this.columnCount + 1);
  }
  toLineRange() {
    return pe.ofLength(1, this.lineCount + 1);
  }
  addToPosition(t) {
    return this.lineCount === 0 ? new Ne(t.lineNumber, t.column + this.columnCount) : new Ne(t.lineNumber + this.lineCount, this.columnCount + 1);
  }
  toString() {
    return `${this.lineCount},${this.columnCount}`;
  }
};
Mt.zero = new Mt(0, 0);
let Gs = Mt;
class xy {
  getOffsetRange(t) {
    return new he(this.getOffset(t.getStartPosition()), this.getOffset(t.getEndPosition()));
  }
  getRange(t) {
    return fe.fromPositions(this.getPosition(t.start), this.getPosition(t.endExclusive));
  }
  getStringReplacement(t) {
    return new Wr.deps.StringReplacement(this.getOffsetRange(t.range), t.text);
  }
  getTextReplacement(t) {
    return new Wr.deps.TextReplacement(this.getRange(t.replaceRange), t.newText);
  }
  getTextEdit(t) {
    const n = t.replacements.map((r) => this.getTextReplacement(r));
    return new Wr.deps.TextEdit(n);
  }
}
const Zu = class Zu {
  static get deps() {
    if (!this._deps)
      throw new Error("Dependencies not set. Call _setDependencies first.");
    return this._deps;
  }
};
Zu._deps = void 0;
let Wr = Zu;
class Ny extends xy {
  constructor(t) {
    super(), this.text = t, this.lineStartOffsetByLineIdx = [], this.lineEndOffsetByLineIdx = [], this.lineStartOffsetByLineIdx.push(0);
    for (let n = 0; n < t.length; n++)
      t.charAt(n) === `
` && (this.lineStartOffsetByLineIdx.push(n + 1), n > 0 && t.charAt(n - 1) === "\r" ? this.lineEndOffsetByLineIdx.push(n - 1) : this.lineEndOffsetByLineIdx.push(n));
    this.lineEndOffsetByLineIdx.push(t.length);
  }
  getOffset(t) {
    const n = this._validatePosition(t);
    return this.lineStartOffsetByLineIdx[n.lineNumber - 1] + n.column - 1;
  }
  _validatePosition(t) {
    if (t.lineNumber < 1)
      return new Ne(1, 1);
    const n = this.textLength.lineCount + 1;
    if (t.lineNumber > n) {
      const s = this.getLineLength(n);
      return new Ne(n, s + 1);
    }
    if (t.column < 1)
      return new Ne(t.lineNumber, 1);
    const r = this.getLineLength(t.lineNumber);
    return t.column - 1 > r ? new Ne(t.lineNumber, r + 1) : t;
  }
  getPosition(t) {
    const n = es(this.lineStartOffsetByLineIdx, (i) => i <= t), r = n + 1, s = t - this.lineStartOffsetByLineIdx[n] + 1;
    return new Ne(r, s);
  }
  get textLength() {
    const t = this.lineStartOffsetByLineIdx.length - 1;
    return new Wr.deps.TextLength(t, this.text.length - this.lineStartOffsetByLineIdx[t]);
  }
  getLineLength(t) {
    return this.lineEndOffsetByLineIdx[t - 1] - this.lineStartOffsetByLineIdx[t - 1];
  }
}
class Ly {
  constructor() {
    this._transformer = void 0;
  }
  get endPositionExclusive() {
    return this.length.addToPosition(new Ne(1, 1));
  }
  get lineRange() {
    return this.length.toLineRange();
  }
  getValue() {
    return this.getValueOfRange(this.length.toRange());
  }
  getValueOfOffsetRange(t) {
    return this.getValueOfRange(this.getTransformer().getRange(t));
  }
  getLineLength(t) {
    return this.getValueOfRange(new fe(t, 1, t, Number.MAX_SAFE_INTEGER)).length;
  }
  getTransformer() {
    return this._transformer || (this._transformer = new Ny(this.getValue())), this._transformer;
  }
  getLineAt(t) {
    return this.getValueOfRange(new fe(t, 1, t, Number.MAX_SAFE_INTEGER));
  }
}
class ky extends Ly {
  constructor(t, n) {
    Tg(n >= 1), super(), this._getLineContent = t, this._lineCount = n;
  }
  getValueOfRange(t) {
    if (t.startLineNumber === t.endLineNumber)
      return this._getLineContent(t.startLineNumber).substring(t.startColumn - 1, t.endColumn - 1);
    let n = this._getLineContent(t.startLineNumber).substring(t.startColumn - 1);
    for (let r = t.startLineNumber + 1; r < t.endLineNumber; r++)
      n += `
` + this._getLineContent(r);
    return n += `
` + this._getLineContent(t.endLineNumber).substring(0, t.endColumn - 1), n;
  }
  getLineLength(t) {
    return this._getLineContent(t).length;
  }
  get length() {
    const t = this._getLineContent(this._lineCount);
    return new Gs(this._lineCount - 1, t.length);
  }
}
class fi extends ky {
  constructor(t) {
    super((n) => t[n - 1], t.length);
  }
}
class Ln {
  static joinReplacements(t, n) {
    if (t.length === 0)
      throw new Ge();
    if (t.length === 1)
      return t[0];
    const r = t[0].range.getStartPosition(), s = t[t.length - 1].range.getEndPosition();
    let i = "";
    for (let a = 0; a < t.length; a++) {
      const o = t[a];
      if (i += o.text, a < t.length - 1) {
        const l = t[a + 1], u = fe.fromPositions(o.range.getEndPosition(), l.range.getStartPosition()), f = n.getValueOfRange(u);
        i += f;
      }
    }
    return new Ln(fe.fromPositions(r, s), i);
  }
  static fromStringReplacement(t, n) {
    return new Ln(n.getTransformer().getRange(t.replaceRange), t.newText);
  }
  static delete(t) {
    return new Ln(t, "");
  }
  constructor(t, n) {
    this.range = t, this.text = n;
  }
  get isEmpty() {
    return this.range.isEmpty() && this.text.length === 0;
  }
  static equals(t, n) {
    return t.range.equalsRange(n.range) && t.text === n.text;
  }
  equals(t) {
    return Ln.equals(this, t);
  }
  removeCommonPrefixAndSuffix(t) {
    return this.removeCommonPrefix(t).removeCommonSuffix(t);
  }
  removeCommonPrefix(t) {
    const n = t.getValueOfRange(this.range).replaceAll(`\r
`, `
`), r = this.text.replaceAll(`\r
`, `
`), s = a0(n, r), i = Gs.ofText(n.substring(0, s)).addToPosition(this.range.getStartPosition()), a = r.substring(s), o = fe.fromPositions(i, this.range.getEndPosition());
    return new Ln(o, a);
  }
  removeCommonSuffix(t) {
    const n = t.getValueOfRange(this.range).replaceAll(`\r
`, `
`), r = this.text.replaceAll(`\r
`, `
`), s = o0(n, r), i = Gs.ofText(n.substring(0, n.length - s)).addToPosition(this.range.getStartPosition()), a = r.substring(0, r.length - s), o = fe.fromPositions(this.range.getStartPosition(), i);
    return new Ln(o, a);
  }
  toString() {
    const t = this.range.getStartPosition(), n = this.range.getEndPosition();
    return `(${t.lineNumber},${t.column} -> ${n.lineNumber},${n.column}): "${this.text}"`;
  }
}
class At {
  static inverse(t, n, r) {
    const s = [];
    let i = 1, a = 1;
    for (const l of t) {
      const u = new At(new pe(i, l.original.startLineNumber), new pe(a, l.modified.startLineNumber));
      u.modified.isEmpty || s.push(u), i = l.original.endLineNumberExclusive, a = l.modified.endLineNumberExclusive;
    }
    const o = new At(new pe(i, n + 1), new pe(a, r + 1));
    return o.modified.isEmpty || s.push(o), s;
  }
  static clip(t, n, r) {
    const s = [];
    for (const i of t) {
      const a = i.original.intersect(n), o = i.modified.intersect(r);
      a && !a.isEmpty && o && !o.isEmpty && s.push(new At(a, o));
    }
    return s;
  }
  constructor(t, n) {
    this.original = t, this.modified = n;
  }
  toString() {
    return `{${this.original.toString()}->${this.modified.toString()}}`;
  }
  flip() {
    return new At(this.modified, this.original);
  }
  join(t) {
    return new At(this.original.join(t.original), this.modified.join(t.modified));
  }
  /**
   * This method assumes that the LineRangeMapping describes a valid diff!
   * I.e. if one range is empty, the other range cannot be the entire document.
   * It avoids various problems when the line range points to non-existing line-numbers.
  */
  toRangeMapping() {
    const t = this.original.toInclusiveRange(), n = this.modified.toInclusiveRange();
    if (t && n)
      return new St(t, n);
    if (this.original.startLineNumber === 1 || this.modified.startLineNumber === 1) {
      if (!(this.modified.startLineNumber === 1 && this.original.startLineNumber === 1))
        throw new Ge("not a valid diff");
      return new St(new fe(this.original.startLineNumber, 1, this.original.endLineNumberExclusive, 1), new fe(this.modified.startLineNumber, 1, this.modified.endLineNumberExclusive, 1));
    } else
      return new St(new fe(this.original.startLineNumber - 1, Number.MAX_SAFE_INTEGER, this.original.endLineNumberExclusive - 1, Number.MAX_SAFE_INTEGER), new fe(this.modified.startLineNumber - 1, Number.MAX_SAFE_INTEGER, this.modified.endLineNumberExclusive - 1, Number.MAX_SAFE_INTEGER));
  }
  /**
   * This method assumes that the LineRangeMapping describes a valid diff!
   * I.e. if one range is empty, the other range cannot be the entire document.
   * It avoids various problems when the line range points to non-existing line-numbers.
  */
  toRangeMapping2(t, n) {
    if (Af(this.original.endLineNumberExclusive, t) && Af(this.modified.endLineNumberExclusive, n))
      return new St(new fe(this.original.startLineNumber, 1, this.original.endLineNumberExclusive, 1), new fe(this.modified.startLineNumber, 1, this.modified.endLineNumberExclusive, 1));
    if (!this.original.isEmpty && !this.modified.isEmpty)
      return new St(fe.fromPositions(new Ne(this.original.startLineNumber, 1), Er(new Ne(this.original.endLineNumberExclusive - 1, Number.MAX_SAFE_INTEGER), t)), fe.fromPositions(new Ne(this.modified.startLineNumber, 1), Er(new Ne(this.modified.endLineNumberExclusive - 1, Number.MAX_SAFE_INTEGER), n)));
    if (this.original.startLineNumber > 1 && this.modified.startLineNumber > 1)
      return new St(fe.fromPositions(Er(new Ne(this.original.startLineNumber - 1, Number.MAX_SAFE_INTEGER), t), Er(new Ne(this.original.endLineNumberExclusive - 1, Number.MAX_SAFE_INTEGER), t)), fe.fromPositions(Er(new Ne(this.modified.startLineNumber - 1, Number.MAX_SAFE_INTEGER), n), Er(new Ne(this.modified.endLineNumberExclusive - 1, Number.MAX_SAFE_INTEGER), n)));
    throw new Ge();
  }
}
function Er(e, t) {
  if (e.lineNumber < 1)
    return new Ne(1, 1);
  if (e.lineNumber > t.length)
    return new Ne(t.length, t[t.length - 1].length + 1);
  const n = t[e.lineNumber - 1];
  return e.column > n.length + 1 ? new Ne(e.lineNumber, n.length + 1) : e;
}
function Af(e, t) {
  return e >= 1 && e <= t.length;
}
class cn extends At {
  static fromRangeMappings(t) {
    const n = pe.join(t.map((s) => pe.fromRangeInclusive(s.originalRange))), r = pe.join(t.map((s) => pe.fromRangeInclusive(s.modifiedRange)));
    return new cn(n, r, t);
  }
  constructor(t, n, r) {
    super(t, n), this.innerChanges = r;
  }
  flip() {
    return new cn(this.modified, this.original, this.innerChanges?.map((t) => t.flip()));
  }
  withInnerChangesFromLineRanges() {
    return new cn(this.original, this.modified, [this.toRangeMapping()]);
  }
}
class St {
  static fromEdit(t) {
    const n = t.getNewRanges();
    return t.replacements.map((s, i) => new St(s.range, n[i]));
  }
  static assertSorted(t) {
    for (let n = 1; n < t.length; n++) {
      const r = t[n - 1], s = t[n];
      if (!(r.originalRange.getEndPosition().isBeforeOrEqual(s.originalRange.getStartPosition()) && r.modifiedRange.getEndPosition().isBeforeOrEqual(s.modifiedRange.getStartPosition())))
        throw new Ge("Range mappings must be sorted");
    }
  }
  constructor(t, n) {
    this.originalRange = t, this.modifiedRange = n;
  }
  toString() {
    return `{${this.originalRange.toString()}->${this.modifiedRange.toString()}}`;
  }
  flip() {
    return new St(this.modifiedRange, this.originalRange);
  }
  /**
   * Creates a single text edit that describes the change from the original to the modified text.
  */
  toTextEdit(t) {
    const n = t.getValueOfRange(this.modifiedRange);
    return new Ln(this.originalRange, n);
  }
}
function xf(e, t, n, r = !1) {
  const s = [];
  for (const i of vy(e.map((a) => Cy(a, t, n)), (a, o) => a.original.intersectsOrTouches(o.original) || a.modified.intersectsOrTouches(o.modified))) {
    const a = i[0], o = i[i.length - 1];
    s.push(new cn(a.original.join(o.original), a.modified.join(o.modified), i.map((l) => l.innerChanges[0])));
  }
  return Wi(() => !r && s.length > 0 && (s[0].modified.startLineNumber !== s[0].original.startLineNumber || n.length.lineCount - s[s.length - 1].modified.endLineNumberExclusive !== t.length.lineCount - s[s.length - 1].original.endLineNumberExclusive) ? !1 : n1(s, (i, a) => a.original.startLineNumber - i.original.endLineNumberExclusive === a.modified.startLineNumber - i.modified.endLineNumberExclusive && // There has to be an unchanged line in between (otherwise both diffs should have been joined)
  i.original.endLineNumberExclusive < a.original.startLineNumber && i.modified.endLineNumberExclusive < a.modified.startLineNumber)), s;
}
function Cy(e, t, n) {
  let r = 0, s = 0;
  e.modifiedRange.endColumn === 1 && e.originalRange.endColumn === 1 && e.originalRange.startLineNumber + r <= e.originalRange.endLineNumber && e.modifiedRange.startLineNumber + r <= e.modifiedRange.endLineNumber && (s = -1), e.modifiedRange.startColumn - 1 >= n.getLineLength(e.modifiedRange.startLineNumber) && e.originalRange.startColumn - 1 >= t.getLineLength(e.originalRange.startLineNumber) && e.originalRange.startLineNumber <= e.originalRange.endLineNumber + s && e.modifiedRange.startLineNumber <= e.modifiedRange.endLineNumber + s && (r = 1);
  const i = new pe(e.originalRange.startLineNumber + r, e.originalRange.endLineNumber + 1 + s), a = new pe(e.modifiedRange.startLineNumber + r, e.modifiedRange.endLineNumber + 1 + s);
  return new cn(i, a, [e]);
}
const Fy = 3;
class _y {
  computeDiff(t, n, r) {
    const i = new Oy(t, n, {
      maxComputationTime: r.maxComputationTimeMs,
      shouldIgnoreTrimWhitespace: r.ignoreTrimWhitespace,
      shouldComputeCharChanges: !0,
      shouldMakePrettyDiff: !0,
      shouldPostProcessCharChanges: !0
    }).computeDiff(), a = [];
    let o = null;
    for (const l of i.changes) {
      let u;
      l.originalEndLineNumber === 0 ? u = new pe(l.originalStartLineNumber + 1, l.originalStartLineNumber + 1) : u = new pe(l.originalStartLineNumber, l.originalEndLineNumber + 1);
      let f;
      l.modifiedEndLineNumber === 0 ? f = new pe(l.modifiedStartLineNumber + 1, l.modifiedStartLineNumber + 1) : f = new pe(l.modifiedStartLineNumber, l.modifiedEndLineNumber + 1);
      let c = new cn(u, f, l.charChanges?.map((d) => new St(new fe(d.originalStartLineNumber, d.originalStartColumn, d.originalEndLineNumber, d.originalEndColumn), new fe(d.modifiedStartLineNumber, d.modifiedStartColumn, d.modifiedEndLineNumber, d.modifiedEndColumn))));
      o && (o.modified.endLineNumberExclusive === c.modified.startLineNumber || o.original.endLineNumberExclusive === c.original.startLineNumber) && (c = new cn(o.original.join(c.original), o.modified.join(c.modified), o.innerChanges && c.innerChanges ? o.innerChanges.concat(c.innerChanges) : void 0), a.pop()), a.push(c), o = c;
    }
    return Wi(() => n1(a, (l, u) => u.original.startLineNumber - l.original.endLineNumberExclusive === u.modified.startLineNumber - l.modified.endLineNumberExclusive && // There has to be an unchanged line in between (otherwise both diffs should have been joined)
    l.original.endLineNumberExclusive < u.original.startLineNumber && l.modified.endLineNumberExclusive < u.modified.startLineNumber)), new Fi(a, [], i.quitEarly);
  }
}
function y1(e, t, n, r) {
  return new Cn(e, t, n).ComputeDiff(r);
}
let Nf = class {
  constructor(t) {
    const n = [], r = [];
    for (let s = 0, i = t.length; s < i; s++)
      n[s] = zo(t[s], 1), r[s] = Go(t[s], 1);
    this.lines = t, this._startColumns = n, this._endColumns = r;
  }
  getElements() {
    const t = [];
    for (let n = 0, r = this.lines.length; n < r; n++)
      t[n] = this.lines[n].substring(this._startColumns[n] - 1, this._endColumns[n] - 1);
    return t;
  }
  getStrictElement(t) {
    return this.lines[t];
  }
  getStartLineNumber(t) {
    return t + 1;
  }
  getEndLineNumber(t) {
    return t + 1;
  }
  createCharSequence(t, n, r) {
    const s = [], i = [], a = [];
    let o = 0;
    for (let l = n; l <= r; l++) {
      const u = this.lines[l], f = t ? this._startColumns[l] : 1, c = t ? this._endColumns[l] : u.length + 1;
      for (let d = f; d < c; d++)
        s[o] = u.charCodeAt(d - 1), i[o] = l + 1, a[o] = d, o++;
      !t && l < r && (s[o] = 10, i[o] = l + 1, a[o] = u.length + 1, o++);
    }
    return new Ty(s, i, a);
  }
};
class Ty {
  constructor(t, n, r) {
    this._charCodes = t, this._lineNumbers = n, this._columns = r;
  }
  toString() {
    return "[" + this._charCodes.map((t, n) => (t === 10 ? "\\n" : String.fromCharCode(t)) + `-(${this._lineNumbers[n]},${this._columns[n]})`).join(", ") + "]";
  }
  _assertIndex(t, n) {
    if (t < 0 || t >= n.length)
      throw new Error("Illegal index");
  }
  getElements() {
    return this._charCodes;
  }
  getStartLineNumber(t) {
    return t > 0 && t === this._lineNumbers.length ? this.getEndLineNumber(t - 1) : (this._assertIndex(t, this._lineNumbers), this._lineNumbers[t]);
  }
  getEndLineNumber(t) {
    return t === -1 ? this.getStartLineNumber(t + 1) : (this._assertIndex(t, this._lineNumbers), this._charCodes[t] === 10 ? this._lineNumbers[t] + 1 : this._lineNumbers[t]);
  }
  getStartColumn(t) {
    return t > 0 && t === this._columns.length ? this.getEndColumn(t - 1) : (this._assertIndex(t, this._columns), this._columns[t]);
  }
  getEndColumn(t) {
    return t === -1 ? this.getStartColumn(t + 1) : (this._assertIndex(t, this._columns), this._charCodes[t] === 10 ? 1 : this._columns[t] + 1);
  }
}
class Hr {
  constructor(t, n, r, s, i, a, o, l) {
    this.originalStartLineNumber = t, this.originalStartColumn = n, this.originalEndLineNumber = r, this.originalEndColumn = s, this.modifiedStartLineNumber = i, this.modifiedStartColumn = a, this.modifiedEndLineNumber = o, this.modifiedEndColumn = l;
  }
  static createFromDiffChange(t, n, r) {
    const s = n.getStartLineNumber(t.originalStart), i = n.getStartColumn(t.originalStart), a = n.getEndLineNumber(t.originalStart + t.originalLength - 1), o = n.getEndColumn(t.originalStart + t.originalLength - 1), l = r.getStartLineNumber(t.modifiedStart), u = r.getStartColumn(t.modifiedStart), f = r.getEndLineNumber(t.modifiedStart + t.modifiedLength - 1), c = r.getEndColumn(t.modifiedStart + t.modifiedLength - 1);
    return new Hr(s, i, a, o, l, u, f, c);
  }
}
function My(e) {
  if (e.length <= 1)
    return e;
  const t = [e[0]];
  let n = t[0];
  for (let r = 1, s = e.length; r < s; r++) {
    const i = e[r], a = i.originalStart - (n.originalStart + n.originalLength), o = i.modifiedStart - (n.modifiedStart + n.modifiedLength);
    Math.min(a, o) < Fy ? (n.originalLength = i.originalStart + i.originalLength - n.originalStart, n.modifiedLength = i.modifiedStart + i.modifiedLength - n.modifiedStart) : (t.push(i), n = i);
  }
  return t;
}
class Ms {
  constructor(t, n, r, s, i) {
    this.originalStartLineNumber = t, this.originalEndLineNumber = n, this.modifiedStartLineNumber = r, this.modifiedEndLineNumber = s, this.charChanges = i;
  }
  static createFromDiffResult(t, n, r, s, i, a, o) {
    let l, u, f, c, d;
    if (n.originalLength === 0 ? (l = r.getStartLineNumber(n.originalStart) - 1, u = 0) : (l = r.getStartLineNumber(n.originalStart), u = r.getEndLineNumber(n.originalStart + n.originalLength - 1)), n.modifiedLength === 0 ? (f = s.getStartLineNumber(n.modifiedStart) - 1, c = 0) : (f = s.getStartLineNumber(n.modifiedStart), c = s.getEndLineNumber(n.modifiedStart + n.modifiedLength - 1)), a && n.originalLength > 0 && n.originalLength < 20 && n.modifiedLength > 0 && n.modifiedLength < 20 && i()) {
      const v = r.createCharSequence(t, n.originalStart, n.originalStart + n.originalLength - 1), D = s.createCharSequence(t, n.modifiedStart, n.modifiedStart + n.modifiedLength - 1);
      if (v.getElements().length > 0 && D.getElements().length > 0) {
        let S = y1(v, D, i, !0).changes;
        o && (S = My(S)), d = [];
        for (let x = 0, N = S.length; x < N; x++)
          d.push(Hr.createFromDiffChange(S[x], v, D));
      }
    }
    return new Ms(l, u, f, c, d);
  }
}
class Oy {
  constructor(t, n, r) {
    this.shouldComputeCharChanges = r.shouldComputeCharChanges, this.shouldPostProcessCharChanges = r.shouldPostProcessCharChanges, this.shouldIgnoreTrimWhitespace = r.shouldIgnoreTrimWhitespace, this.shouldMakePrettyDiff = r.shouldMakePrettyDiff, this.originalLines = t, this.modifiedLines = n, this.original = new Nf(t), this.modified = new Nf(n), this.continueLineDiff = Lf(r.maxComputationTime), this.continueCharDiff = Lf(r.maxComputationTime === 0 ? 0 : Math.min(r.maxComputationTime, 5e3));
  }
  computeDiff() {
    if (this.original.lines.length === 1 && this.original.lines[0].length === 0)
      return this.modified.lines.length === 1 && this.modified.lines[0].length === 0 ? {
        quitEarly: !1,
        changes: []
      } : {
        quitEarly: !1,
        changes: [{
          originalStartLineNumber: 1,
          originalEndLineNumber: 1,
          modifiedStartLineNumber: 1,
          modifiedEndLineNumber: this.modified.lines.length,
          charChanges: void 0
        }]
      };
    if (this.modified.lines.length === 1 && this.modified.lines[0].length === 0)
      return {
        quitEarly: !1,
        changes: [{
          originalStartLineNumber: 1,
          originalEndLineNumber: this.original.lines.length,
          modifiedStartLineNumber: 1,
          modifiedEndLineNumber: 1,
          charChanges: void 0
        }]
      };
    const t = y1(this.original, this.modified, this.continueLineDiff, this.shouldMakePrettyDiff), n = t.changes, r = t.quitEarly;
    if (this.shouldIgnoreTrimWhitespace) {
      const o = [];
      for (let l = 0, u = n.length; l < u; l++)
        o.push(Ms.createFromDiffResult(this.shouldIgnoreTrimWhitespace, n[l], this.original, this.modified, this.continueCharDiff, this.shouldComputeCharChanges, this.shouldPostProcessCharChanges));
      return {
        quitEarly: r,
        changes: o
      };
    }
    const s = [];
    let i = 0, a = 0;
    for (let o = -1, l = n.length; o < l; o++) {
      const u = o + 1 < l ? n[o + 1] : null, f = u ? u.originalStart : this.originalLines.length, c = u ? u.modifiedStart : this.modifiedLines.length;
      for (; i < f && a < c; ) {
        const d = this.originalLines[i], v = this.modifiedLines[a];
        if (d !== v) {
          {
            let D = zo(d, 1), S = zo(v, 1);
            for (; D > 1 && S > 1; ) {
              const x = d.charCodeAt(D - 2), N = v.charCodeAt(S - 2);
              if (x !== N)
                break;
              D--, S--;
            }
            (D > 1 || S > 1) && this._pushTrimWhitespaceCharChange(s, i + 1, 1, D, a + 1, 1, S);
          }
          {
            let D = Go(d, 1), S = Go(v, 1);
            const x = d.length + 1, N = v.length + 1;
            for (; D < x && S < N; ) {
              const k = d.charCodeAt(D - 1), y = d.charCodeAt(S - 1);
              if (k !== y)
                break;
              D++, S++;
            }
            (D < x || S < N) && this._pushTrimWhitespaceCharChange(s, i + 1, D, x, a + 1, S, N);
          }
        }
        i++, a++;
      }
      u && (s.push(Ms.createFromDiffResult(this.shouldIgnoreTrimWhitespace, u, this.original, this.modified, this.continueCharDiff, this.shouldComputeCharChanges, this.shouldPostProcessCharChanges)), i += u.originalLength, a += u.modifiedLength);
    }
    return {
      quitEarly: r,
      changes: s
    };
  }
  _pushTrimWhitespaceCharChange(t, n, r, s, i, a, o) {
    if (this._mergeTrimWhitespaceCharChange(t, n, r, s, i, a, o))
      return;
    let l;
    this.shouldComputeCharChanges && (l = [new Hr(n, r, n, s, i, a, i, o)]), t.push(new Ms(n, n, i, i, l));
  }
  _mergeTrimWhitespaceCharChange(t, n, r, s, i, a, o) {
    const l = t.length;
    if (l === 0)
      return !1;
    const u = t[l - 1];
    return u.originalEndLineNumber === 0 || u.modifiedEndLineNumber === 0 ? !1 : u.originalEndLineNumber === n && u.modifiedEndLineNumber === i ? (this.shouldComputeCharChanges && u.charChanges && u.charChanges.push(new Hr(n, r, n, s, i, a, i, o)), !0) : u.originalEndLineNumber + 1 === n && u.modifiedEndLineNumber + 1 === i ? (u.originalEndLineNumber = n, u.modifiedEndLineNumber = i, this.shouldComputeCharChanges && u.charChanges && u.charChanges.push(new Hr(n, r, n, s, i, a, i, o)), !0) : !1;
  }
}
function zo(e, t) {
  const n = s0(e);
  return n === -1 ? t : n + 1;
}
function Go(e, t) {
  const n = i0(e);
  return n === -1 ? t : n + 2;
}
function Lf(e) {
  if (e === 0)
    return () => !0;
  const t = Date.now();
  return () => Date.now() - t < e;
}
class fn {
  static trivial(t, n) {
    return new fn([new Oe(he.ofLength(t.length), he.ofLength(n.length))], !1);
  }
  static trivialTimedOut(t, n) {
    return new fn([new Oe(he.ofLength(t.length), he.ofLength(n.length))], !0);
  }
  constructor(t, n) {
    this.diffs = t, this.hitTimeout = n;
  }
}
class Oe {
  static invert(t, n) {
    const r = [];
    return wy(t, (s, i) => {
      r.push(Oe.fromOffsetPairs(s ? s.getEndExclusives() : ln.zero, i ? i.getStarts() : new ln(n, (s ? s.seq2Range.endExclusive - s.seq1Range.endExclusive : 0) + n)));
    }), r;
  }
  static fromOffsetPairs(t, n) {
    return new Oe(new he(t.offset1, n.offset1), new he(t.offset2, n.offset2));
  }
  static assertSorted(t) {
    let n;
    for (const r of t) {
      if (n && !(n.seq1Range.endExclusive <= r.seq1Range.start && n.seq2Range.endExclusive <= r.seq2Range.start))
        throw new Ge("Sequence diffs must be sorted");
      n = r;
    }
  }
  constructor(t, n) {
    this.seq1Range = t, this.seq2Range = n;
  }
  swap() {
    return new Oe(this.seq2Range, this.seq1Range);
  }
  toString() {
    return `${this.seq1Range} <-> ${this.seq2Range}`;
  }
  join(t) {
    return new Oe(this.seq1Range.join(t.seq1Range), this.seq2Range.join(t.seq2Range));
  }
  delta(t) {
    return t === 0 ? this : new Oe(this.seq1Range.delta(t), this.seq2Range.delta(t));
  }
  deltaStart(t) {
    return t === 0 ? this : new Oe(this.seq1Range.deltaStart(t), this.seq2Range.deltaStart(t));
  }
  deltaEnd(t) {
    return t === 0 ? this : new Oe(this.seq1Range.deltaEnd(t), this.seq2Range.deltaEnd(t));
  }
  intersect(t) {
    const n = this.seq1Range.intersect(t.seq1Range), r = this.seq2Range.intersect(t.seq2Range);
    if (!(!n || !r))
      return new Oe(n, r);
  }
  getStarts() {
    return new ln(this.seq1Range.start, this.seq2Range.start);
  }
  getEndExclusives() {
    return new ln(this.seq1Range.endExclusive, this.seq2Range.endExclusive);
  }
}
const Jn = class Jn {
  constructor(t, n) {
    this.offset1 = t, this.offset2 = n;
  }
  toString() {
    return `${this.offset1} <-> ${this.offset2}`;
  }
  delta(t) {
    return t === 0 ? this : new Jn(this.offset1 + t, this.offset2 + t);
  }
  equals(t) {
    return this.offset1 === t.offset1 && this.offset2 === t.offset2;
  }
};
Jn.zero = new Jn(0, 0), Jn.max = new Jn(Number.MAX_SAFE_INTEGER, Number.MAX_SAFE_INTEGER);
let ln = Jn;
const Ea = class Ea {
  isValid() {
    return !0;
  }
};
Ea.instance = new Ea();
let Js = Ea;
class Ry {
  constructor(t) {
    if (this.timeout = t, this.startTime = Date.now(), this.valid = !0, t <= 0)
      throw new Ge("timeout must be positive");
  }
  // Recommendation: Set a log-point `{this.disable()}` in the body
  isValid() {
    return !(Date.now() - this.startTime < this.timeout) && this.valid && (this.valid = !1), this.valid;
  }
}
class Xa {
  constructor(t, n) {
    this.width = t, this.height = n, this.array = [], this.array = new Array(t * n);
  }
  get(t, n) {
    return this.array[t + n * this.width];
  }
  set(t, n, r) {
    this.array[t + n * this.width] = r;
  }
}
function Jo(e) {
  return e === 32 || e === 9;
}
const qs = class qs {
  static getKey(t) {
    let n = this.chrKeys.get(t);
    return n === void 0 && (n = this.chrKeys.size, this.chrKeys.set(t, n)), n;
  }
  constructor(t, n, r) {
    this.range = t, this.lines = n, this.source = r, this.histogram = [];
    let s = 0;
    for (let i = t.startLineNumber - 1; i < t.endLineNumberExclusive - 1; i++) {
      const a = n[i];
      for (let l = 0; l < a.length; l++) {
        s++;
        const u = a[l], f = qs.getKey(u);
        this.histogram[f] = (this.histogram[f] || 0) + 1;
      }
      s++;
      const o = qs.getKey(`
`);
      this.histogram[o] = (this.histogram[o] || 0) + 1;
    }
    this.totalCount = s;
  }
  computeSimilarity(t) {
    let n = 0;
    const r = Math.max(this.histogram.length, t.histogram.length);
    for (let s = 0; s < r; s++)
      n += Math.abs((this.histogram[s] ?? 0) - (t.histogram[s] ?? 0));
    return 1 - n / (this.totalCount + t.totalCount);
  }
};
qs.chrKeys = /* @__PURE__ */ new Map();
let Xi = qs;
class Py {
  compute(t, n, r = Js.instance, s) {
    if (t.length === 0 || n.length === 0)
      return fn.trivial(t, n);
    const i = new Xa(t.length, n.length), a = new Xa(t.length, n.length), o = new Xa(t.length, n.length);
    for (let D = 0; D < t.length; D++)
      for (let S = 0; S < n.length; S++) {
        if (!r.isValid())
          return fn.trivialTimedOut(t, n);
        const x = D === 0 ? 0 : i.get(D - 1, S), N = S === 0 ? 0 : i.get(D, S - 1);
        let k;
        t.getElement(D) === n.getElement(S) ? (D === 0 || S === 0 ? k = 0 : k = i.get(D - 1, S - 1), D > 0 && S > 0 && a.get(D - 1, S - 1) === 3 && (k += o.get(D - 1, S - 1)), k += s ? s(D, S) : 1) : k = -1;
        const y = Math.max(x, N, k);
        if (y === k) {
          const b = D > 0 && S > 0 ? o.get(D - 1, S - 1) : 0;
          o.set(D, S, b + 1), a.set(D, S, 3);
        } else y === x ? (o.set(D, S, 0), a.set(D, S, 1)) : y === N && (o.set(D, S, 0), a.set(D, S, 2));
        i.set(D, S, y);
      }
    const l = [];
    let u = t.length, f = n.length;
    function c(D, S) {
      (D + 1 !== u || S + 1 !== f) && l.push(new Oe(new he(D + 1, u), new he(S + 1, f))), u = D, f = S;
    }
    let d = t.length - 1, v = n.length - 1;
    for (; d >= 0 && v >= 0; )
      a.get(d, v) === 3 ? (c(d, v), d--, v--) : a.get(d, v) === 1 ? d-- : v--;
    return c(-1, -1), l.reverse(), new fn(l, !1);
  }
}
class b1 {
  compute(t, n, r = Js.instance) {
    if (t.length === 0 || n.length === 0)
      return fn.trivial(t, n);
    const s = t, i = n;
    function a(S, x) {
      for (; S < s.length && x < i.length && s.getElement(S) === i.getElement(x); )
        S++, x++;
      return S;
    }
    let o = 0;
    const l = new Iy();
    l.set(0, a(0, 0));
    const u = new $y();
    u.set(0, l.get(0) === 0 ? null : new kf(null, 0, 0, l.get(0)));
    let f = 0;
    e: for (; ; ) {
      if (o++, !r.isValid())
        return fn.trivialTimedOut(s, i);
      const S = -Math.min(o, i.length + o % 2), x = Math.min(o, s.length + o % 2);
      for (f = S; f <= x; f += 2) {
        const N = f === x ? -1 : l.get(f + 1), k = f === S ? -1 : l.get(f - 1) + 1, y = Math.min(Math.max(N, k), s.length), b = y - f;
        if (y > s.length || b > i.length)
          continue;
        const h = a(y, b);
        l.set(f, h);
        const m = y === N ? u.get(f + 1) : u.get(f - 1);
        if (u.set(f, h !== y ? new kf(m, y, b, h - y) : m), l.get(f) === s.length && l.get(f) - f === i.length)
          break e;
      }
    }
    let c = u.get(f);
    const d = [];
    let v = s.length, D = i.length;
    for (; ; ) {
      const S = c ? c.x + c.length : 0, x = c ? c.y + c.length : 0;
      if ((S !== v || x !== D) && d.push(new Oe(new he(S, v), new he(x, D))), !c)
        break;
      v = c.x, D = c.y, c = c.prev;
    }
    return d.reverse(), new fn(d, !1);
  }
}
class kf {
  constructor(t, n, r, s) {
    this.prev = t, this.x = n, this.y = r, this.length = s;
  }
}
class Iy {
  constructor() {
    this.positiveArr = new Int32Array(10), this.negativeArr = new Int32Array(10);
  }
  get(t) {
    return t < 0 ? (t = -t - 1, this.negativeArr[t]) : this.positiveArr[t];
  }
  set(t, n) {
    if (t < 0) {
      if (t = -t - 1, t >= this.negativeArr.length) {
        const r = this.negativeArr;
        this.negativeArr = new Int32Array(r.length * 2), this.negativeArr.set(r);
      }
      this.negativeArr[t] = n;
    } else {
      if (t >= this.positiveArr.length) {
        const r = this.positiveArr;
        this.positiveArr = new Int32Array(r.length * 2), this.positiveArr.set(r);
      }
      this.positiveArr[t] = n;
    }
  }
}
class $y {
  constructor() {
    this.positiveArr = [], this.negativeArr = [];
  }
  get(t) {
    return t < 0 ? (t = -t - 1, this.negativeArr[t]) : this.positiveArr[t];
  }
  set(t, n) {
    t < 0 ? (t = -t - 1, this.negativeArr[t] = n) : this.positiveArr[t] = n;
  }
}
class Zi {
  constructor(t, n, r) {
    this.lines = t, this.range = n, this.considerWhitespaceChanges = r, this.elements = [], this.firstElementOffsetByLineIdx = [], this.lineStartOffsets = [], this.trimmedWsLengthsByLineIdx = [], this.firstElementOffsetByLineIdx.push(0);
    for (let s = this.range.startLineNumber; s <= this.range.endLineNumber; s++) {
      let i = t[s - 1], a = 0;
      s === this.range.startLineNumber && this.range.startColumn > 1 && (a = this.range.startColumn - 1, i = i.substring(a)), this.lineStartOffsets.push(a);
      let o = 0;
      if (!r) {
        const u = i.trimStart();
        o = i.length - u.length, i = u.trimEnd();
      }
      this.trimmedWsLengthsByLineIdx.push(o);
      const l = s === this.range.endLineNumber ? Math.min(this.range.endColumn - 1 - a - o, i.length) : i.length;
      for (let u = 0; u < l; u++)
        this.elements.push(i.charCodeAt(u));
      s < this.range.endLineNumber && (this.elements.push(10), this.firstElementOffsetByLineIdx.push(this.elements.length));
    }
  }
  toString() {
    return `Slice: "${this.text}"`;
  }
  get text() {
    return this.getText(new he(0, this.length));
  }
  getText(t) {
    return this.elements.slice(t.start, t.endExclusive).map((n) => String.fromCharCode(n)).join("");
  }
  getElement(t) {
    return this.elements[t];
  }
  get length() {
    return this.elements.length;
  }
  getBoundaryScore(t) {
    const n = _f(t > 0 ? this.elements[t - 1] : -1), r = _f(t < this.elements.length ? this.elements[t] : -1);
    if (n === 7 && r === 8)
      return 0;
    if (n === 8)
      return 150;
    let s = 0;
    return n !== r && (s += 10, n === 0 && r === 1 && (s += 1)), s += Ff(n), s += Ff(r), s;
  }
  translateOffset(t, n = "right") {
    const r = es(this.firstElementOffsetByLineIdx, (i) => i <= t), s = t - this.firstElementOffsetByLineIdx[r];
    return new Ne(this.range.startLineNumber + r, 1 + this.lineStartOffsets[r] + s + (s === 0 && n === "left" ? 0 : this.trimmedWsLengthsByLineIdx[r]));
  }
  translateRange(t) {
    const n = this.translateOffset(t.start, "right"), r = this.translateOffset(t.endExclusive, "left");
    return r.isBefore(n) ? fe.fromPositions(r, r) : fe.fromPositions(n, r);
  }
  /**
   * Finds the word that contains the character at the given offset
   */
  findWordContaining(t) {
    if (t < 0 || t >= this.elements.length || !Ar(this.elements[t]))
      return;
    let n = t;
    for (; n > 0 && Ar(this.elements[n - 1]); )
      n--;
    let r = t;
    for (; r < this.elements.length && Ar(this.elements[r]); )
      r++;
    return new he(n, r);
  }
  /** fooBar has the two sub-words foo and bar */
  findSubWordContaining(t) {
    if (t < 0 || t >= this.elements.length || !Ar(this.elements[t]))
      return;
    let n = t;
    for (; n > 0 && Ar(this.elements[n - 1]) && !Cf(this.elements[n]); )
      n--;
    let r = t;
    for (; r < this.elements.length && Ar(this.elements[r]) && !Cf(this.elements[r]); )
      r++;
    return new he(n, r);
  }
  countLinesIn(t) {
    return this.translateOffset(t.endExclusive).lineNumber - this.translateOffset(t.start).lineNumber;
  }
  isStronglyEqual(t, n) {
    return this.elements[t] === this.elements[n];
  }
  extendToFullLines(t) {
    const n = Zr(this.firstElementOffsetByLineIdx, (s) => s <= t.start) ?? 0, r = Ay(this.firstElementOffsetByLineIdx, (s) => t.endExclusive <= s) ?? this.elements.length;
    return new he(n, r);
  }
}
function Ar(e) {
  return e >= 97 && e <= 122 || e >= 65 && e <= 90 || e >= 48 && e <= 57;
}
function Cf(e) {
  return e >= 65 && e <= 90;
}
const By = {
  0: 0,
  1: 0,
  2: 0,
  3: 10,
  4: 2,
  5: 30,
  6: 3,
  7: 10,
  8: 10
};
function Ff(e) {
  return By[e];
}
function _f(e) {
  return e === 10 ? 8 : e === 13 ? 7 : Jo(e) ? 6 : e >= 97 && e <= 122 ? 0 : e >= 65 && e <= 90 ? 1 : e >= 48 && e <= 57 ? 2 : e === -1 ? 3 : e === 44 || e === 59 ? 5 : 4;
}
function Vy(e, t, n, r, s, i) {
  let { moves: a, excludedChanges: o } = Uy(e, t, n, i);
  if (!i.isValid())
    return [];
  const l = e.filter((f) => !o.has(f)), u = qy(l, r, s, t, n, i);
  return Sy(a, u), a = Wy(a), a = a.filter((f) => {
    const c = f.original.toOffsetRange().slice(t).map((v) => v.trim());
    return c.join(`
`).length >= 15 && jy(c, (v) => v.length >= 2) >= 2;
  }), a = Hy(e, a), a;
}
function jy(e, t) {
  let n = 0;
  for (const r of e)
    t(r) && n++;
  return n;
}
function Uy(e, t, n, r) {
  const s = [], i = e.filter((l) => l.modified.isEmpty && l.original.length >= 3).map((l) => new Xi(l.original, t, l)), a = new Set(e.filter((l) => l.original.isEmpty && l.modified.length >= 3).map((l) => new Xi(l.modified, n, l))), o = /* @__PURE__ */ new Set();
  for (const l of i) {
    let u = -1, f;
    for (const c of a) {
      const d = l.computeSimilarity(c);
      d > u && (u = d, f = c);
    }
    if (u > 0.9 && f && (a.delete(f), s.push(new At(l.range, f.range)), o.add(l.source), o.add(f.source)), !r.isValid())
      return { moves: s, excludedChanges: o };
  }
  return { moves: s, excludedChanges: o };
}
function qy(e, t, n, r, s, i) {
  const a = [], o = new ay();
  for (const d of e)
    for (let v = d.original.startLineNumber; v < d.original.endLineNumberExclusive - 2; v++) {
      const D = `${t[v - 1]}:${t[v + 1 - 1]}:${t[v + 2 - 1]}`;
      o.add(D, { range: new pe(v, v + 3) });
    }
  const l = [];
  e.sort(_s((d) => d.modified.startLineNumber, Ts));
  for (const d of e) {
    let v = [];
    for (let D = d.modified.startLineNumber; D < d.modified.endLineNumberExclusive - 2; D++) {
      const S = `${n[D - 1]}:${n[D + 1 - 1]}:${n[D + 2 - 1]}`, x = new pe(D, D + 3), N = [];
      o.forEach(S, ({ range: k }) => {
        for (const b of v)
          if (b.originalLineRange.endLineNumberExclusive + 1 === k.endLineNumberExclusive && b.modifiedLineRange.endLineNumberExclusive + 1 === x.endLineNumberExclusive) {
            b.originalLineRange = new pe(b.originalLineRange.startLineNumber, k.endLineNumberExclusive), b.modifiedLineRange = new pe(b.modifiedLineRange.startLineNumber, x.endLineNumberExclusive), N.push(b);
            return;
          }
        const y = {
          modifiedLineRange: x,
          originalLineRange: k
        };
        l.push(y), N.push(y);
      }), v = N;
    }
    if (!i.isValid())
      return [];
  }
  l.sort(Ey(_s((d) => d.modifiedLineRange.length, Ts)));
  const u = new Yt(), f = new Yt();
  for (const d of l) {
    const v = d.modifiedLineRange.startLineNumber - d.originalLineRange.startLineNumber, D = u.subtractFrom(d.modifiedLineRange), S = f.subtractFrom(d.originalLineRange).getWithDelta(v), x = D.getIntersection(S);
    for (const N of x.ranges) {
      if (N.length < 3)
        continue;
      const k = N, y = N.delta(-v);
      a.push(new At(y, k)), u.addRange(k), f.addRange(y);
    }
  }
  a.sort(_s((d) => d.original.startLineNumber, Ts));
  const c = new Ki(e);
  for (let d = 0; d < a.length; d++) {
    const v = a[d], D = c.findLastMonotonous((m) => m.original.startLineNumber <= v.original.startLineNumber), S = Zr(e, (m) => m.modified.startLineNumber <= v.modified.startLineNumber), x = Math.max(v.original.startLineNumber - D.original.startLineNumber, v.modified.startLineNumber - S.modified.startLineNumber), N = c.findLastMonotonous((m) => m.original.startLineNumber < v.original.endLineNumberExclusive), k = Zr(e, (m) => m.modified.startLineNumber < v.modified.endLineNumberExclusive), y = Math.max(N.original.endLineNumberExclusive - v.original.endLineNumberExclusive, k.modified.endLineNumberExclusive - v.modified.endLineNumberExclusive);
    let b;
    for (b = 0; b < x; b++) {
      const m = v.original.startLineNumber - b - 1, p = v.modified.startLineNumber - b - 1;
      if (m > r.length || p > s.length || u.contains(p) || f.contains(m) || !Tf(r[m - 1], s[p - 1], i))
        break;
    }
    b > 0 && (f.addRange(new pe(v.original.startLineNumber - b, v.original.startLineNumber)), u.addRange(new pe(v.modified.startLineNumber - b, v.modified.startLineNumber)));
    let h;
    for (h = 0; h < y; h++) {
      const m = v.original.endLineNumberExclusive + h, p = v.modified.endLineNumberExclusive + h;
      if (m > r.length || p > s.length || u.contains(p) || f.contains(m) || !Tf(r[m - 1], s[p - 1], i))
        break;
    }
    h > 0 && (f.addRange(new pe(v.original.endLineNumberExclusive, v.original.endLineNumberExclusive + h)), u.addRange(new pe(v.modified.endLineNumberExclusive, v.modified.endLineNumberExclusive + h))), (b > 0 || h > 0) && (a[d] = new At(new pe(v.original.startLineNumber - b, v.original.endLineNumberExclusive + h), new pe(v.modified.startLineNumber - b, v.modified.endLineNumberExclusive + h)));
  }
  return a;
}
function Tf(e, t, n) {
  if (e.trim() === t.trim())
    return !0;
  if (e.length > 300 && t.length > 300)
    return !1;
  const s = new b1().compute(new Zi([e], new fe(1, 1, 1, e.length), !1), new Zi([t], new fe(1, 1, 1, t.length), !1), n);
  let i = 0;
  const a = Oe.invert(s.diffs, e.length);
  for (const f of a)
    f.seq1Range.forEach((c) => {
      Jo(e.charCodeAt(c)) || i++;
    });
  function o(f) {
    let c = 0;
    for (let d = 0; d < e.length; d++)
      Jo(f.charCodeAt(d)) || c++;
    return c;
  }
  const l = o(e.length > t.length ? e : t);
  return i / l > 0.6 && l > 10;
}
function Wy(e) {
  if (e.length === 0)
    return e;
  e.sort(_s((n) => n.original.startLineNumber, Ts));
  const t = [e[0]];
  for (let n = 1; n < e.length; n++) {
    const r = t[t.length - 1], s = e[n], i = s.original.startLineNumber - r.original.endLineNumberExclusive, a = s.modified.startLineNumber - r.modified.endLineNumberExclusive;
    if (i >= 0 && a >= 0 && i + a <= 2) {
      t[t.length - 1] = r.join(s);
      continue;
    }
    t.push(s);
  }
  return t;
}
function Hy(e, t) {
  const n = new Ki(e);
  return t = t.filter((r) => {
    const s = n.findLastMonotonous((o) => o.original.startLineNumber < r.original.endLineNumberExclusive) || new At(new pe(1, 1), new pe(1, 1)), i = Zr(e, (o) => o.modified.startLineNumber < r.modified.endLineNumberExclusive);
    return s !== i;
  }), t;
}
function Mf(e, t, n) {
  let r = n;
  return r = Of(e, t, r), r = Of(e, t, r), r = Yy(e, t, r), r;
}
function Of(e, t, n) {
  if (n.length === 0)
    return n;
  const r = [];
  r.push(n[0]);
  for (let i = 1; i < n.length; i++) {
    const a = r[r.length - 1];
    let o = n[i];
    if (o.seq1Range.isEmpty || o.seq2Range.isEmpty) {
      const l = o.seq1Range.start - a.seq1Range.endExclusive;
      let u;
      for (u = 1; u <= l && !(e.getElement(o.seq1Range.start - u) !== e.getElement(o.seq1Range.endExclusive - u) || t.getElement(o.seq2Range.start - u) !== t.getElement(o.seq2Range.endExclusive - u)); u++)
        ;
      if (u--, u === l) {
        r[r.length - 1] = new Oe(new he(a.seq1Range.start, o.seq1Range.endExclusive - l), new he(a.seq2Range.start, o.seq2Range.endExclusive - l));
        continue;
      }
      o = o.delta(-u);
    }
    r.push(o);
  }
  const s = [];
  for (let i = 0; i < r.length - 1; i++) {
    const a = r[i + 1];
    let o = r[i];
    if (o.seq1Range.isEmpty || o.seq2Range.isEmpty) {
      const l = a.seq1Range.start - o.seq1Range.endExclusive;
      let u;
      for (u = 0; u < l && !(!e.isStronglyEqual(o.seq1Range.start + u, o.seq1Range.endExclusive + u) || !t.isStronglyEqual(o.seq2Range.start + u, o.seq2Range.endExclusive + u)); u++)
        ;
      if (u === l) {
        r[i + 1] = new Oe(new he(o.seq1Range.start + l, a.seq1Range.endExclusive), new he(o.seq2Range.start + l, a.seq2Range.endExclusive));
        continue;
      }
      u > 0 && (o = o.delta(u));
    }
    s.push(o);
  }
  return r.length > 0 && s.push(r[r.length - 1]), s;
}
function Yy(e, t, n) {
  if (!e.getBoundaryScore || !t.getBoundaryScore)
    return n;
  for (let r = 0; r < n.length; r++) {
    const s = r > 0 ? n[r - 1] : void 0, i = n[r], a = r + 1 < n.length ? n[r + 1] : void 0, o = new he(s ? s.seq1Range.endExclusive + 1 : 0, a ? a.seq1Range.start - 1 : e.length), l = new he(s ? s.seq2Range.endExclusive + 1 : 0, a ? a.seq2Range.start - 1 : t.length);
    i.seq1Range.isEmpty ? n[r] = Rf(i, e, t, o, l) : i.seq2Range.isEmpty && (n[r] = Rf(i.swap(), t, e, l, o).swap());
  }
  return n;
}
function Rf(e, t, n, r, s) {
  let a = 1;
  for (; e.seq1Range.start - a >= r.start && e.seq2Range.start - a >= s.start && n.isStronglyEqual(e.seq2Range.start - a, e.seq2Range.endExclusive - a) && a < 100; )
    a++;
  a--;
  let o = 0;
  for (; e.seq1Range.start + o < r.endExclusive && e.seq2Range.endExclusive + o < s.endExclusive && n.isStronglyEqual(e.seq2Range.start + o, e.seq2Range.endExclusive + o) && o < 100; )
    o++;
  if (a === 0 && o === 0)
    return e;
  let l = 0, u = -1;
  for (let f = -a; f <= o; f++) {
    const c = e.seq2Range.start + f, d = e.seq2Range.endExclusive + f, v = e.seq1Range.start + f, D = t.getBoundaryScore(v) + n.getBoundaryScore(c) + n.getBoundaryScore(d);
    D > u && (u = D, l = f);
  }
  return e.delta(l);
}
function zy(e, t, n) {
  const r = [];
  for (const s of n) {
    const i = r[r.length - 1];
    if (!i) {
      r.push(s);
      continue;
    }
    s.seq1Range.start - i.seq1Range.endExclusive <= 2 || s.seq2Range.start - i.seq2Range.endExclusive <= 2 ? r[r.length - 1] = new Oe(i.seq1Range.join(s.seq1Range), i.seq2Range.join(s.seq2Range)) : r.push(s);
  }
  return r;
}
function Pf(e, t, n, r, s = !1) {
  const i = Oe.invert(n, e.length), a = [];
  let o = new ln(0, 0);
  function l(f, c) {
    if (f.offset1 < o.offset1 || f.offset2 < o.offset2)
      return;
    const d = r(e, f.offset1), v = r(t, f.offset2);
    if (!d || !v)
      return;
    let D = new Oe(d, v);
    const S = D.intersect(c);
    let x = S.seq1Range.length, N = S.seq2Range.length;
    for (; i.length > 0; ) {
      const k = i[0];
      if (!(k.seq1Range.intersects(D.seq1Range) || k.seq2Range.intersects(D.seq2Range)))
        break;
      const b = r(e, k.seq1Range.start), h = r(t, k.seq2Range.start), m = new Oe(b, h), p = m.intersect(k);
      if (x += p.seq1Range.length, N += p.seq2Range.length, D = D.join(m), D.seq1Range.endExclusive >= k.seq1Range.endExclusive)
        i.shift();
      else
        break;
    }
    (s && x + N < D.seq1Range.length + D.seq2Range.length || x + N < (D.seq1Range.length + D.seq2Range.length) * 2 / 3) && a.push(D), o = D.getEndExclusives();
  }
  for (; i.length > 0; ) {
    const f = i.shift();
    f.seq1Range.isEmpty || (l(f.getStarts(), f), l(f.getEndExclusives().delta(-1), f));
  }
  return Gy(n, a);
}
function Gy(e, t) {
  const n = [];
  for (; e.length > 0 || t.length > 0; ) {
    const r = e[0], s = t[0];
    let i;
    r && (!s || r.seq1Range.start < s.seq1Range.start) ? i = e.shift() : i = t.shift(), n.length > 0 && n[n.length - 1].seq1Range.endExclusive >= i.seq1Range.start ? n[n.length - 1] = n[n.length - 1].join(i) : n.push(i);
  }
  return n;
}
function Jy(e, t, n) {
  let r = n;
  if (r.length === 0)
    return r;
  let s = 0, i;
  do {
    i = !1;
    const o = [
      r[0]
    ];
    for (let l = 1; l < r.length; l++) {
      let c = function(v, D) {
        const S = new he(f.seq1Range.endExclusive, u.seq1Range.start);
        return e.getText(S).replace(/\s/g, "").length <= 4 && (v.seq1Range.length + v.seq2Range.length > 5 || D.seq1Range.length + D.seq2Range.length > 5);
      };
      var a = c;
      const u = r[l], f = o[o.length - 1];
      c(f, u) ? (i = !0, o[o.length - 1] = o[o.length - 1].join(u)) : o.push(u);
    }
    r = o;
  } while (s++ < 10 && i);
  return r;
}
function Qy(e, t, n) {
  let r = n;
  if (r.length === 0)
    return r;
  let s = 0, i;
  do {
    i = !1;
    const l = [
      r[0]
    ];
    for (let u = 1; u < r.length; u++) {
      let d = function(D, S) {
        const x = new he(c.seq1Range.endExclusive, f.seq1Range.start);
        if (e.countLinesIn(x) > 5 || x.length > 500)
          return !1;
        const k = e.getText(x).trim();
        if (k.length > 20 || k.split(/\r\n|\r|\n/).length > 1)
          return !1;
        const y = e.countLinesIn(D.seq1Range), b = D.seq1Range.length, h = t.countLinesIn(D.seq2Range), m = D.seq2Range.length, p = e.countLinesIn(S.seq1Range), E = S.seq1Range.length, w = t.countLinesIn(S.seq2Range), L = S.seq2Range.length, C = 130;
        function A(_) {
          return Math.min(_, C);
        }
        return Math.pow(Math.pow(A(y * 40 + b), 1.5) + Math.pow(A(h * 40 + m), 1.5), 1.5) + Math.pow(Math.pow(A(p * 40 + E), 1.5) + Math.pow(A(w * 40 + L), 1.5), 1.5) > (C ** 1.5) ** 1.5 * 1.3;
      };
      var o = d;
      const f = r[u], c = l[l.length - 1];
      d(c, f) ? (i = !0, l[l.length - 1] = l[l.length - 1].join(f)) : l.push(f);
    }
    r = l;
  } while (s++ < 10 && i);
  const a = [];
  return Dy(r, (l, u, f) => {
    let c = u;
    function d(k) {
      return k.length > 0 && k.trim().length <= 3 && u.seq1Range.length + u.seq2Range.length > 100;
    }
    const v = e.extendToFullLines(u.seq1Range), D = e.getText(new he(v.start, u.seq1Range.start));
    d(D) && (c = c.deltaStart(-D.length));
    const S = e.getText(new he(u.seq1Range.endExclusive, v.endExclusive));
    d(S) && (c = c.deltaEnd(S.length));
    const x = Oe.fromOffsetPairs(l ? l.getEndExclusives() : ln.zero, f ? f.getStarts() : ln.max), N = c.intersect(x);
    a.length > 0 && N.getStarts().equals(a[a.length - 1].getEndExclusives()) ? a[a.length - 1] = a[a.length - 1].join(N) : a.push(N);
  }), a;
}
class If {
  constructor(t, n) {
    this.trimmedHash = t, this.lines = n;
  }
  getElement(t) {
    return this.trimmedHash[t];
  }
  get length() {
    return this.trimmedHash.length;
  }
  getBoundaryScore(t) {
    const n = t === 0 ? 0 : $f(this.lines[t - 1]), r = t === this.lines.length ? 0 : $f(this.lines[t]);
    return 1e3 - (n + r);
  }
  getText(t) {
    return this.lines.slice(t.start, t.endExclusive).join(`
`);
  }
  isStronglyEqual(t, n) {
    return this.lines[t] === this.lines[n];
  }
}
function $f(e) {
  let t = 0;
  for (; t < e.length && (e.charCodeAt(t) === 32 || e.charCodeAt(t) === 9); )
    t++;
  return t;
}
class Ky {
  constructor() {
    this.dynamicProgrammingDiffing = new Py(), this.myersDiffingAlgorithm = new b1();
  }
  computeDiff(t, n, r) {
    if (t.length <= 1 && by(t, n, (p, E) => p === E))
      return new Fi([], [], !1);
    if (t.length === 1 && t[0].length === 0 || n.length === 1 && n[0].length === 0)
      return new Fi([
        new cn(new pe(1, t.length + 1), new pe(1, n.length + 1), [
          new St(new fe(1, 1, t.length, t[t.length - 1].length + 1), new fe(1, 1, n.length, n[n.length - 1].length + 1))
        ])
      ], [], !1);
    const s = r.maxComputationTimeMs === 0 ? Js.instance : new Ry(r.maxComputationTimeMs), i = !r.ignoreTrimWhitespace, a = /* @__PURE__ */ new Map();
    function o(p) {
      let E = a.get(p);
      return E === void 0 && (E = a.size, a.set(p, E)), E;
    }
    const l = t.map((p) => o(p.trim())), u = n.map((p) => o(p.trim())), f = new If(l, t), c = new If(u, n), d = f.length + c.length < 1700 ? this.dynamicProgrammingDiffing.compute(f, c, s, (p, E) => t[p] === n[E] ? n[E].length === 0 ? 0.1 : 1 + Math.log(1 + n[E].length) : 0.99) : this.myersDiffingAlgorithm.compute(f, c, s);
    let v = d.diffs, D = d.hitTimeout;
    v = Mf(f, c, v), v = Jy(f, c, v);
    const S = [], x = (p) => {
      if (i)
        for (let E = 0; E < p; E++) {
          const w = N + E, L = k + E;
          if (t[w] !== n[L]) {
            const C = this.refineDiff(t, n, new Oe(new he(w, w + 1), new he(L, L + 1)), s, i, r);
            for (const A of C.mappings)
              S.push(A);
            C.hitTimeout && (D = !0);
          }
        }
    };
    let N = 0, k = 0;
    for (const p of v) {
      Wi(() => p.seq1Range.start - N === p.seq2Range.start - k);
      const E = p.seq1Range.start - N;
      x(E), N = p.seq1Range.endExclusive, k = p.seq2Range.endExclusive;
      const w = this.refineDiff(t, n, p, s, i, r);
      w.hitTimeout && (D = !0);
      for (const L of w.mappings)
        S.push(L);
    }
    x(t.length - N);
    const y = new fi(t), b = new fi(n), h = xf(S, y, b);
    let m = [];
    return r.computeMoves && (m = this.computeMoves(h, t, n, l, u, s, i, r)), Wi(() => {
      function p(w, L) {
        if (w.lineNumber < 1 || w.lineNumber > L.length)
          return !1;
        const C = L[w.lineNumber - 1];
        return !(w.column < 1 || w.column > C.length + 1);
      }
      function E(w, L) {
        return !(w.startLineNumber < 1 || w.startLineNumber > L.length + 1 || w.endLineNumberExclusive < 1 || w.endLineNumberExclusive > L.length + 1);
      }
      for (const w of h) {
        if (!w.innerChanges)
          return !1;
        for (const L of w.innerChanges)
          if (!(p(L.modifiedRange.getStartPosition(), n) && p(L.modifiedRange.getEndPosition(), n) && p(L.originalRange.getStartPosition(), t) && p(L.originalRange.getEndPosition(), t)))
            return !1;
        if (!E(w.modified, n) || !E(w.original, t))
          return !1;
      }
      return !0;
    }), new Fi(h, m, D);
  }
  computeMoves(t, n, r, s, i, a, o, l) {
    return Vy(t, n, r, s, i, a).map((c) => {
      const d = this.refineDiff(n, r, new Oe(c.original.toOffsetRange(), c.modified.toOffsetRange()), a, o, l), v = xf(d.mappings, new fi(n), new fi(r), !0);
      return new yy(c, v);
    });
  }
  refineDiff(t, n, r, s, i, a) {
    const l = Xy(r).toRangeMapping2(t, n), u = new Zi(t, l.originalRange, i), f = new Zi(n, l.modifiedRange, i), c = u.length + f.length < 500 ? this.dynamicProgrammingDiffing.compute(u, f, s) : this.myersDiffingAlgorithm.compute(u, f, s);
    let d = c.diffs;
    return d = Mf(u, f, d), d = Pf(u, f, d, (D, S) => D.findWordContaining(S)), a.extendToSubwords && (d = Pf(u, f, d, (D, S) => D.findSubWordContaining(S), !0)), d = zy(u, f, d), d = Qy(u, f, d), {
      mappings: d.map((D) => new St(u.translateRange(D.seq1Range), f.translateRange(D.seq2Range))),
      hitTimeout: c.hitTimeout
    };
  }
}
function Xy(e) {
  return new At(new pe(e.seq1Range.start + 1, e.seq1Range.endExclusive + 1), new pe(e.seq2Range.start + 1, e.seq2Range.endExclusive + 1));
}
const Bf = {
  getLegacy: () => new _y(),
  getDefault: () => new Ky()
};
function Tn(e, t) {
  const n = Math.pow(10, t);
  return Math.round(e * n) / n;
}
class U {
  constructor(t, n, r, s = 1) {
    this._rgbaBrand = void 0, this.r = Math.min(255, Math.max(0, t)) | 0, this.g = Math.min(255, Math.max(0, n)) | 0, this.b = Math.min(255, Math.max(0, r)) | 0, this.a = Tn(Math.max(Math.min(1, s), 0), 3);
  }
  static equals(t, n) {
    return t.r === n.r && t.g === n.g && t.b === n.b && t.a === n.a;
  }
}
class Et {
  constructor(t, n, r, s) {
    this._hslaBrand = void 0, this.h = Math.max(Math.min(360, t), 0) | 0, this.s = Tn(Math.max(Math.min(1, n), 0), 3), this.l = Tn(Math.max(Math.min(1, r), 0), 3), this.a = Tn(Math.max(Math.min(1, s), 0), 3);
  }
  static equals(t, n) {
    return t.h === n.h && t.s === n.s && t.l === n.l && t.a === n.a;
  }
  /**
   * Converts an RGB color value to HSL. Conversion formula
   * adapted from http://en.wikipedia.org/wiki/HSL_color_space.
   * Assumes r, g, and b are contained in the set [0, 255] and
   * returns h in the set [0, 360], s, and l in the set [0, 1].
   */
  static fromRGBA(t) {
    const n = t.r / 255, r = t.g / 255, s = t.b / 255, i = t.a, a = Math.max(n, r, s), o = Math.min(n, r, s);
    let l = 0, u = 0;
    const f = (o + a) / 2, c = a - o;
    if (c > 0) {
      switch (u = Math.min(f <= 0.5 ? c / (2 * f) : c / (2 - 2 * f), 1), a) {
        case n:
          l = (r - s) / c + (r < s ? 6 : 0);
          break;
        case r:
          l = (s - n) / c + 2;
          break;
        case s:
          l = (n - r) / c + 4;
          break;
      }
      l *= 60, l = Math.round(l);
    }
    return new Et(l, u, f, i);
  }
  static _hue2rgb(t, n, r) {
    return r < 0 && (r += 1), r > 1 && (r -= 1), r < 1 / 6 ? t + (n - t) * 6 * r : r < 1 / 2 ? n : r < 2 / 3 ? t + (n - t) * (2 / 3 - r) * 6 : t;
  }
  /**
   * Converts an HSL color value to RGB. Conversion formula
   * adapted from http://en.wikipedia.org/wiki/HSL_color_space.
   * Assumes h in the set [0, 360] s, and l are contained in the set [0, 1] and
   * returns r, g, and b in the set [0, 255].
   */
  static toRGBA(t) {
    const n = t.h / 360, { s: r, l: s, a: i } = t;
    let a, o, l;
    if (r === 0)
      a = o = l = s;
    else {
      const u = s < 0.5 ? s * (1 + r) : s + r - s * r, f = 2 * s - u;
      a = Et._hue2rgb(f, u, n + 1 / 3), o = Et._hue2rgb(f, u, n), l = Et._hue2rgb(f, u, n - 1 / 3);
    }
    return new U(Math.round(a * 255), Math.round(o * 255), Math.round(l * 255), i);
  }
}
class Fr {
  constructor(t, n, r, s) {
    this._hsvaBrand = void 0, this.h = Math.max(Math.min(360, t), 0) | 0, this.s = Tn(Math.max(Math.min(1, n), 0), 3), this.v = Tn(Math.max(Math.min(1, r), 0), 3), this.a = Tn(Math.max(Math.min(1, s), 0), 3);
  }
  static equals(t, n) {
    return t.h === n.h && t.s === n.s && t.v === n.v && t.a === n.a;
  }
  // from http://www.rapidtables.com/convert/color/rgb-to-hsv.htm
  static fromRGBA(t) {
    const n = t.r / 255, r = t.g / 255, s = t.b / 255, i = Math.max(n, r, s), a = Math.min(n, r, s), o = i - a, l = i === 0 ? 0 : o / i;
    let u;
    return o === 0 ? u = 0 : i === n ? u = ((r - s) / o % 6 + 6) % 6 : i === r ? u = (s - n) / o + 2 : u = (n - r) / o + 4, new Fr(Math.round(u * 60), l, i, t.a);
  }
  // from http://www.rapidtables.com/convert/color/hsv-to-rgb.htm
  static toRGBA(t) {
    const { h: n, s: r, v: s, a: i } = t, a = s * r, o = a * (1 - Math.abs(n / 60 % 2 - 1)), l = s - a;
    let [u, f, c] = [0, 0, 0];
    return n < 60 ? (u = a, f = o) : n < 120 ? (u = o, f = a) : n < 180 ? (f = a, c = o) : n < 240 ? (f = o, c = a) : n < 300 ? (u = o, c = a) : n <= 360 && (u = a, c = o), u = Math.round((u + l) * 255), f = Math.round((f + l) * 255), c = Math.round((c + l) * 255), new U(u, f, c, i);
  }
}
var ye;
let ea = (ye = class {
  static fromHex(t) {
    return ye.Format.CSS.parseHex(t) || ye.red;
  }
  static equals(t, n) {
    return !t && !n ? !0 : !t || !n ? !1 : t.equals(n);
  }
  get hsla() {
    return this._hsla ? this._hsla : Et.fromRGBA(this.rgba);
  }
  get hsva() {
    return this._hsva ? this._hsva : Fr.fromRGBA(this.rgba);
  }
  constructor(t) {
    if (t)
      if (t instanceof U)
        this.rgba = t;
      else if (t instanceof Et)
        this._hsla = t, this.rgba = Et.toRGBA(t);
      else if (t instanceof Fr)
        this._hsva = t, this.rgba = Fr.toRGBA(t);
      else
        throw new Error("Invalid color ctor argument");
    else throw new Error("Color needs a value");
  }
  equals(t) {
    return !!t && U.equals(this.rgba, t.rgba) && Et.equals(this.hsla, t.hsla) && Fr.equals(this.hsva, t.hsva);
  }
  /**
   * http://www.w3.org/TR/WCAG20/#relativeluminancedef
   * Returns the number in the set [0, 1]. O => Darkest Black. 1 => Lightest white.
   */
  getRelativeLuminance() {
    const t = ye._relativeLuminanceForComponent(this.rgba.r), n = ye._relativeLuminanceForComponent(this.rgba.g), r = ye._relativeLuminanceForComponent(this.rgba.b), s = 0.2126 * t + 0.7152 * n + 0.0722 * r;
    return Tn(s, 4);
  }
  static _relativeLuminanceForComponent(t) {
    const n = t / 255;
    return n <= 0.03928 ? n / 12.92 : Math.pow((n + 0.055) / 1.055, 2.4);
  }
  /**
   *	http://24ways.org/2010/calculating-color-contrast
   *  Return 'true' if lighter color otherwise 'false'
   */
  isLighter() {
    return (this.rgba.r * 299 + this.rgba.g * 587 + this.rgba.b * 114) / 1e3 >= 128;
  }
  isLighterThan(t) {
    const n = this.getRelativeLuminance(), r = t.getRelativeLuminance();
    return n > r;
  }
  isDarkerThan(t) {
    const n = this.getRelativeLuminance(), r = t.getRelativeLuminance();
    return n < r;
  }
  lighten(t) {
    return new ye(new Et(this.hsla.h, this.hsla.s, this.hsla.l + this.hsla.l * t, this.hsla.a));
  }
  darken(t) {
    return new ye(new Et(this.hsla.h, this.hsla.s, this.hsla.l - this.hsla.l * t, this.hsla.a));
  }
  transparent(t) {
    const { r: n, g: r, b: s, a: i } = this.rgba;
    return new ye(new U(n, r, s, i * t));
  }
  isTransparent() {
    return this.rgba.a === 0;
  }
  isOpaque() {
    return this.rgba.a === 1;
  }
  opposite() {
    return new ye(new U(255 - this.rgba.r, 255 - this.rgba.g, 255 - this.rgba.b, this.rgba.a));
  }
  /**
   * Mixes the current color with the provided color based on the given factor.
   * @param color The color to mix with
   * @param factor The factor of mixing (0 means this color, 1 means the input color, 0.5 means equal mix)
   * @returns A new color representing the mix
   */
  mix(t, n = 0.5) {
    const r = Math.min(Math.max(n, 0), 1), s = this.rgba, i = t.rgba, a = s.r + (i.r - s.r) * r, o = s.g + (i.g - s.g) * r, l = s.b + (i.b - s.b) * r, u = s.a + (i.a - s.a) * r;
    return new ye(new U(a, o, l, u));
  }
  makeOpaque(t) {
    if (this.isOpaque() || t.rgba.a !== 1)
      return this;
    const { r: n, g: r, b: s, a: i } = this.rgba;
    return new ye(new U(t.rgba.r - i * (t.rgba.r - n), t.rgba.g - i * (t.rgba.g - r), t.rgba.b - i * (t.rgba.b - s), 1));
  }
  toString() {
    return this._toString || (this._toString = ye.Format.CSS.format(this)), this._toString;
  }
  toNumber32Bit() {
    return this._toNumber32Bit || (this._toNumber32Bit = (this.rgba.r << 24 | this.rgba.g << 16 | this.rgba.b << 8 | this.rgba.a * 255 << 0) >>> 0), this._toNumber32Bit;
  }
  static getLighterColor(t, n, r) {
    if (t.isLighterThan(n))
      return t;
    r = r || 0.5;
    const s = t.getRelativeLuminance(), i = n.getRelativeLuminance();
    return r = r * (i - s) / i, t.lighten(r);
  }
  static getDarkerColor(t, n, r) {
    if (t.isDarkerThan(n))
      return t;
    r = r || 0.5;
    const s = t.getRelativeLuminance(), i = n.getRelativeLuminance();
    return r = r * (s - i) / s, t.darken(r);
  }
}, ye.white = new ye(new U(255, 255, 255, 1)), ye.black = new ye(new U(0, 0, 0, 1)), ye.red = new ye(new U(255, 0, 0, 1)), ye.blue = new ye(new U(0, 0, 255, 1)), ye.green = new ye(new U(0, 255, 0, 1)), ye.cyan = new ye(new U(0, 255, 255, 1)), ye.lightgrey = new ye(new U(211, 211, 211, 1)), ye.transparent = new ye(new U(0, 0, 0, 0)), ye);
(function(e) {
  (function(t) {
    (function(n) {
      function r(S) {
        return S.rgba.a === 1 ? `rgb(${S.rgba.r}, ${S.rgba.g}, ${S.rgba.b})` : e.Format.CSS.formatRGBA(S);
      }
      n.formatRGB = r;
      function s(S) {
        return `rgba(${S.rgba.r}, ${S.rgba.g}, ${S.rgba.b}, ${+S.rgba.a.toFixed(2)})`;
      }
      n.formatRGBA = s;
      function i(S) {
        return S.hsla.a === 1 ? `hsl(${S.hsla.h}, ${Math.round(S.hsla.s * 100)}%, ${Math.round(S.hsla.l * 100)}%)` : e.Format.CSS.formatHSLA(S);
      }
      n.formatHSL = i;
      function a(S) {
        return `hsla(${S.hsla.h}, ${Math.round(S.hsla.s * 100)}%, ${Math.round(S.hsla.l * 100)}%, ${S.hsla.a.toFixed(2)})`;
      }
      n.formatHSLA = a;
      function o(S) {
        const x = S.toString(16);
        return x.length !== 2 ? "0" + x : x;
      }
      function l(S) {
        return `#${o(S.rgba.r)}${o(S.rgba.g)}${o(S.rgba.b)}`;
      }
      n.formatHex = l;
      function u(S, x = !1) {
        return x && S.rgba.a === 1 ? e.Format.CSS.formatHex(S) : `#${o(S.rgba.r)}${o(S.rgba.g)}${o(S.rgba.b)}${o(Math.round(S.rgba.a * 255))}`;
      }
      n.formatHexA = u;
      function f(S) {
        return S.isOpaque() ? e.Format.CSS.formatHex(S) : e.Format.CSS.formatRGBA(S);
      }
      n.format = f;
      function c(S) {
        if (S === "transparent")
          return e.transparent;
        if (S.startsWith("#"))
          return v(S);
        if (S.startsWith("rgba(")) {
          const x = S.match(/rgba\((?<r>(?:\+|-)?\d+), *(?<g>(?:\+|-)?\d+), *(?<b>(?:\+|-)?\d+), *(?<a>(?:\+|-)?\d+(\.\d+)?)\)/);
          if (!x)
            throw new Error("Invalid color format " + S);
          const N = parseInt(x.groups?.r ?? "0"), k = parseInt(x.groups?.g ?? "0"), y = parseInt(x.groups?.b ?? "0"), b = parseFloat(x.groups?.a ?? "0");
          return new e(new U(N, k, y, b));
        }
        if (S.startsWith("rgb(")) {
          const x = S.match(/rgb\((?<r>(?:\+|-)?\d+), *(?<g>(?:\+|-)?\d+), *(?<b>(?:\+|-)?\d+)\)/);
          if (!x)
            throw new Error("Invalid color format " + S);
          const N = parseInt(x.groups?.r ?? "0"), k = parseInt(x.groups?.g ?? "0"), y = parseInt(x.groups?.b ?? "0");
          return new e(new U(N, k, y));
        }
        return d(S);
      }
      n.parse = c;
      function d(S) {
        switch (S) {
          case "aliceblue":
            return new e(new U(240, 248, 255, 1));
          case "antiquewhite":
            return new e(new U(250, 235, 215, 1));
          case "aqua":
            return new e(new U(0, 255, 255, 1));
          case "aquamarine":
            return new e(new U(127, 255, 212, 1));
          case "azure":
            return new e(new U(240, 255, 255, 1));
          case "beige":
            return new e(new U(245, 245, 220, 1));
          case "bisque":
            return new e(new U(255, 228, 196, 1));
          case "black":
            return new e(new U(0, 0, 0, 1));
          case "blanchedalmond":
            return new e(new U(255, 235, 205, 1));
          case "blue":
            return new e(new U(0, 0, 255, 1));
          case "blueviolet":
            return new e(new U(138, 43, 226, 1));
          case "brown":
            return new e(new U(165, 42, 42, 1));
          case "burlywood":
            return new e(new U(222, 184, 135, 1));
          case "cadetblue":
            return new e(new U(95, 158, 160, 1));
          case "chartreuse":
            return new e(new U(127, 255, 0, 1));
          case "chocolate":
            return new e(new U(210, 105, 30, 1));
          case "coral":
            return new e(new U(255, 127, 80, 1));
          case "cornflowerblue":
            return new e(new U(100, 149, 237, 1));
          case "cornsilk":
            return new e(new U(255, 248, 220, 1));
          case "crimson":
            return new e(new U(220, 20, 60, 1));
          case "cyan":
            return new e(new U(0, 255, 255, 1));
          case "darkblue":
            return new e(new U(0, 0, 139, 1));
          case "darkcyan":
            return new e(new U(0, 139, 139, 1));
          case "darkgoldenrod":
            return new e(new U(184, 134, 11, 1));
          case "darkgray":
            return new e(new U(169, 169, 169, 1));
          case "darkgreen":
            return new e(new U(0, 100, 0, 1));
          case "darkgrey":
            return new e(new U(169, 169, 169, 1));
          case "darkkhaki":
            return new e(new U(189, 183, 107, 1));
          case "darkmagenta":
            return new e(new U(139, 0, 139, 1));
          case "darkolivegreen":
            return new e(new U(85, 107, 47, 1));
          case "darkorange":
            return new e(new U(255, 140, 0, 1));
          case "darkorchid":
            return new e(new U(153, 50, 204, 1));
          case "darkred":
            return new e(new U(139, 0, 0, 1));
          case "darksalmon":
            return new e(new U(233, 150, 122, 1));
          case "darkseagreen":
            return new e(new U(143, 188, 143, 1));
          case "darkslateblue":
            return new e(new U(72, 61, 139, 1));
          case "darkslategray":
            return new e(new U(47, 79, 79, 1));
          case "darkslategrey":
            return new e(new U(47, 79, 79, 1));
          case "darkturquoise":
            return new e(new U(0, 206, 209, 1));
          case "darkviolet":
            return new e(new U(148, 0, 211, 1));
          case "deeppink":
            return new e(new U(255, 20, 147, 1));
          case "deepskyblue":
            return new e(new U(0, 191, 255, 1));
          case "dimgray":
            return new e(new U(105, 105, 105, 1));
          case "dimgrey":
            return new e(new U(105, 105, 105, 1));
          case "dodgerblue":
            return new e(new U(30, 144, 255, 1));
          case "firebrick":
            return new e(new U(178, 34, 34, 1));
          case "floralwhite":
            return new e(new U(255, 250, 240, 1));
          case "forestgreen":
            return new e(new U(34, 139, 34, 1));
          case "fuchsia":
            return new e(new U(255, 0, 255, 1));
          case "gainsboro":
            return new e(new U(220, 220, 220, 1));
          case "ghostwhite":
            return new e(new U(248, 248, 255, 1));
          case "gold":
            return new e(new U(255, 215, 0, 1));
          case "goldenrod":
            return new e(new U(218, 165, 32, 1));
          case "gray":
            return new e(new U(128, 128, 128, 1));
          case "green":
            return new e(new U(0, 128, 0, 1));
          case "greenyellow":
            return new e(new U(173, 255, 47, 1));
          case "grey":
            return new e(new U(128, 128, 128, 1));
          case "honeydew":
            return new e(new U(240, 255, 240, 1));
          case "hotpink":
            return new e(new U(255, 105, 180, 1));
          case "indianred":
            return new e(new U(205, 92, 92, 1));
          case "indigo":
            return new e(new U(75, 0, 130, 1));
          case "ivory":
            return new e(new U(255, 255, 240, 1));
          case "khaki":
            return new e(new U(240, 230, 140, 1));
          case "lavender":
            return new e(new U(230, 230, 250, 1));
          case "lavenderblush":
            return new e(new U(255, 240, 245, 1));
          case "lawngreen":
            return new e(new U(124, 252, 0, 1));
          case "lemonchiffon":
            return new e(new U(255, 250, 205, 1));
          case "lightblue":
            return new e(new U(173, 216, 230, 1));
          case "lightcoral":
            return new e(new U(240, 128, 128, 1));
          case "lightcyan":
            return new e(new U(224, 255, 255, 1));
          case "lightgoldenrodyellow":
            return new e(new U(250, 250, 210, 1));
          case "lightgray":
            return new e(new U(211, 211, 211, 1));
          case "lightgreen":
            return new e(new U(144, 238, 144, 1));
          case "lightgrey":
            return new e(new U(211, 211, 211, 1));
          case "lightpink":
            return new e(new U(255, 182, 193, 1));
          case "lightsalmon":
            return new e(new U(255, 160, 122, 1));
          case "lightseagreen":
            return new e(new U(32, 178, 170, 1));
          case "lightskyblue":
            return new e(new U(135, 206, 250, 1));
          case "lightslategray":
            return new e(new U(119, 136, 153, 1));
          case "lightslategrey":
            return new e(new U(119, 136, 153, 1));
          case "lightsteelblue":
            return new e(new U(176, 196, 222, 1));
          case "lightyellow":
            return new e(new U(255, 255, 224, 1));
          case "lime":
            return new e(new U(0, 255, 0, 1));
          case "limegreen":
            return new e(new U(50, 205, 50, 1));
          case "linen":
            return new e(new U(250, 240, 230, 1));
          case "magenta":
            return new e(new U(255, 0, 255, 1));
          case "maroon":
            return new e(new U(128, 0, 0, 1));
          case "mediumaquamarine":
            return new e(new U(102, 205, 170, 1));
          case "mediumblue":
            return new e(new U(0, 0, 205, 1));
          case "mediumorchid":
            return new e(new U(186, 85, 211, 1));
          case "mediumpurple":
            return new e(new U(147, 112, 219, 1));
          case "mediumseagreen":
            return new e(new U(60, 179, 113, 1));
          case "mediumslateblue":
            return new e(new U(123, 104, 238, 1));
          case "mediumspringgreen":
            return new e(new U(0, 250, 154, 1));
          case "mediumturquoise":
            return new e(new U(72, 209, 204, 1));
          case "mediumvioletred":
            return new e(new U(199, 21, 133, 1));
          case "midnightblue":
            return new e(new U(25, 25, 112, 1));
          case "mintcream":
            return new e(new U(245, 255, 250, 1));
          case "mistyrose":
            return new e(new U(255, 228, 225, 1));
          case "moccasin":
            return new e(new U(255, 228, 181, 1));
          case "navajowhite":
            return new e(new U(255, 222, 173, 1));
          case "navy":
            return new e(new U(0, 0, 128, 1));
          case "oldlace":
            return new e(new U(253, 245, 230, 1));
          case "olive":
            return new e(new U(128, 128, 0, 1));
          case "olivedrab":
            return new e(new U(107, 142, 35, 1));
          case "orange":
            return new e(new U(255, 165, 0, 1));
          case "orangered":
            return new e(new U(255, 69, 0, 1));
          case "orchid":
            return new e(new U(218, 112, 214, 1));
          case "palegoldenrod":
            return new e(new U(238, 232, 170, 1));
          case "palegreen":
            return new e(new U(152, 251, 152, 1));
          case "paleturquoise":
            return new e(new U(175, 238, 238, 1));
          case "palevioletred":
            return new e(new U(219, 112, 147, 1));
          case "papayawhip":
            return new e(new U(255, 239, 213, 1));
          case "peachpuff":
            return new e(new U(255, 218, 185, 1));
          case "peru":
            return new e(new U(205, 133, 63, 1));
          case "pink":
            return new e(new U(255, 192, 203, 1));
          case "plum":
            return new e(new U(221, 160, 221, 1));
          case "powderblue":
            return new e(new U(176, 224, 230, 1));
          case "purple":
            return new e(new U(128, 0, 128, 1));
          case "rebeccapurple":
            return new e(new U(102, 51, 153, 1));
          case "red":
            return new e(new U(255, 0, 0, 1));
          case "rosybrown":
            return new e(new U(188, 143, 143, 1));
          case "royalblue":
            return new e(new U(65, 105, 225, 1));
          case "saddlebrown":
            return new e(new U(139, 69, 19, 1));
          case "salmon":
            return new e(new U(250, 128, 114, 1));
          case "sandybrown":
            return new e(new U(244, 164, 96, 1));
          case "seagreen":
            return new e(new U(46, 139, 87, 1));
          case "seashell":
            return new e(new U(255, 245, 238, 1));
          case "sienna":
            return new e(new U(160, 82, 45, 1));
          case "silver":
            return new e(new U(192, 192, 192, 1));
          case "skyblue":
            return new e(new U(135, 206, 235, 1));
          case "slateblue":
            return new e(new U(106, 90, 205, 1));
          case "slategray":
            return new e(new U(112, 128, 144, 1));
          case "slategrey":
            return new e(new U(112, 128, 144, 1));
          case "snow":
            return new e(new U(255, 250, 250, 1));
          case "springgreen":
            return new e(new U(0, 255, 127, 1));
          case "steelblue":
            return new e(new U(70, 130, 180, 1));
          case "tan":
            return new e(new U(210, 180, 140, 1));
          case "teal":
            return new e(new U(0, 128, 128, 1));
          case "thistle":
            return new e(new U(216, 191, 216, 1));
          case "tomato":
            return new e(new U(255, 99, 71, 1));
          case "turquoise":
            return new e(new U(64, 224, 208, 1));
          case "violet":
            return new e(new U(238, 130, 238, 1));
          case "wheat":
            return new e(new U(245, 222, 179, 1));
          case "white":
            return new e(new U(255, 255, 255, 1));
          case "whitesmoke":
            return new e(new U(245, 245, 245, 1));
          case "yellow":
            return new e(new U(255, 255, 0, 1));
          case "yellowgreen":
            return new e(new U(154, 205, 50, 1));
          default:
            return null;
        }
      }
      function v(S) {
        const x = S.length;
        if (x === 0 || S.charCodeAt(0) !== 35)
          return null;
        if (x === 7) {
          const N = 16 * D(S.charCodeAt(1)) + D(S.charCodeAt(2)), k = 16 * D(S.charCodeAt(3)) + D(S.charCodeAt(4)), y = 16 * D(S.charCodeAt(5)) + D(S.charCodeAt(6));
          return new e(new U(N, k, y, 1));
        }
        if (x === 9) {
          const N = 16 * D(S.charCodeAt(1)) + D(S.charCodeAt(2)), k = 16 * D(S.charCodeAt(3)) + D(S.charCodeAt(4)), y = 16 * D(S.charCodeAt(5)) + D(S.charCodeAt(6)), b = 16 * D(S.charCodeAt(7)) + D(S.charCodeAt(8));
          return new e(new U(N, k, y, b / 255));
        }
        if (x === 4) {
          const N = D(S.charCodeAt(1)), k = D(S.charCodeAt(2)), y = D(S.charCodeAt(3));
          return new e(new U(16 * N + N, 16 * k + k, 16 * y + y));
        }
        if (x === 5) {
          const N = D(S.charCodeAt(1)), k = D(S.charCodeAt(2)), y = D(S.charCodeAt(3)), b = D(S.charCodeAt(4));
          return new e(new U(16 * N + N, 16 * k + k, 16 * y + y, (16 * b + b) / 255));
        }
        return null;
      }
      n.parseHex = v;
      function D(S) {
        switch (S) {
          case 48:
            return 0;
          case 49:
            return 1;
          case 50:
            return 2;
          case 51:
            return 3;
          case 52:
            return 4;
          case 53:
            return 5;
          case 54:
            return 6;
          case 55:
            return 7;
          case 56:
            return 8;
          case 57:
            return 9;
          case 97:
            return 10;
          case 65:
            return 10;
          case 98:
            return 11;
          case 66:
            return 11;
          case 99:
            return 12;
          case 67:
            return 12;
          case 100:
            return 13;
          case 68:
            return 13;
          case 101:
            return 14;
          case 69:
            return 14;
          case 102:
            return 15;
          case 70:
            return 15;
        }
        return 0;
      }
    })(t.CSS || (t.CSS = {}));
  })(e.Format || (e.Format = {}));
})(ea || (ea = {}));
function v1(e) {
  const t = [];
  for (const n of e) {
    const r = Number(n);
    (r || r === 0 && n.replace(/\s/g, "") !== "") && t.push(r);
  }
  return t;
}
function au(e, t, n, r) {
  return {
    red: e / 255,
    blue: n / 255,
    green: t / 255,
    alpha: r
  };
}
function bs(e, t) {
  const n = t.index, r = t[0].length;
  if (n === void 0)
    return;
  const s = e.positionAt(n);
  return {
    startLineNumber: s.lineNumber,
    startColumn: s.column,
    endLineNumber: s.lineNumber,
    endColumn: s.column + r
  };
}
function Zy(e, t) {
  if (!e)
    return;
  const n = ea.Format.CSS.parseHex(t);
  if (n)
    return {
      range: e,
      color: au(n.rgba.r, n.rgba.g, n.rgba.b, n.rgba.a)
    };
}
function Vf(e, t, n) {
  if (!e || t.length !== 1)
    return;
  const s = t[0].values(), i = v1(s);
  return {
    range: e,
    color: au(i[0], i[1], i[2], n ? i[3] : 1)
  };
}
function jf(e, t, n) {
  if (!e || t.length !== 1)
    return;
  const s = t[0].values(), i = v1(s), a = new ea(new Et(i[0], i[1] / 100, i[2] / 100, n ? i[3] : 1));
  return {
    range: e,
    color: au(a.rgba.r, a.rgba.g, a.rgba.b, a.rgba.a)
  };
}
function vs(e, t) {
  return typeof e == "string" ? [...e.matchAll(t)] : e.findMatches(t);
}
function eb(e) {
  const t = [], n = new RegExp(`\\b(rgb|rgba|hsl|hsla)(\\([0-9\\s,.\\%]*\\))|^(#)([A-Fa-f0-9]{3})\\b|^(#)([A-Fa-f0-9]{4})\\b|^(#)([A-Fa-f0-9]{6})\\b|^(#)([A-Fa-f0-9]{8})\\b|(?<=['"\\s])(#)([A-Fa-f0-9]{3})\\b|(?<=['"\\s])(#)([A-Fa-f0-9]{4})\\b|(?<=['"\\s])(#)([A-Fa-f0-9]{6})\\b|(?<=['"\\s])(#)([A-Fa-f0-9]{8})\\b`, "gm"), r = vs(e, n);
  if (r.length > 0)
    for (const s of r) {
      const i = s.filter((u) => u !== void 0), a = i[1], o = i[2];
      if (!o)
        continue;
      let l;
      if (a === "rgb") {
        const u = /^\(\s*(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9][0-9]|[0-9])\s*,\s*(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9][0-9]|[0-9])\s*,\s*(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9][0-9]|[0-9])\s*\)$/gm;
        l = Vf(bs(e, s), vs(o, u), !1);
      } else if (a === "rgba") {
        const u = /^\(\s*(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9][0-9]|[0-9])\s*,\s*(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9][0-9]|[0-9])\s*,\s*(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9][0-9]|[0-9])\s*,\s*(0[.][0-9]+|[.][0-9]+|[01][.]|[01])\s*\)$/gm;
        l = Vf(bs(e, s), vs(o, u), !0);
      } else if (a === "hsl") {
        const u = /^\(\s*((?:360(?:\.0+)?|(?:36[0]|3[0-5][0-9]|[12][0-9][0-9]|[1-9]?[0-9])(?:\.\d+)?))\s*[\s,]\s*(100|\d{1,2}[.]\d*|\d{1,2})%\s*[\s,]\s*(100|\d{1,2}[.]\d*|\d{1,2})%\s*\)$/gm;
        l = jf(bs(e, s), vs(o, u), !1);
      } else if (a === "hsla") {
        const u = /^\(\s*((?:360(?:\.0+)?|(?:36[0]|3[0-5][0-9]|[12][0-9][0-9]|[1-9]?[0-9])(?:\.\d+)?))\s*[\s,]\s*(100|\d{1,2}[.]\d*|\d{1,2})%\s*[\s,]\s*(100|\d{1,2}[.]\d*|\d{1,2})%\s*[\s,]\s*(0[.][0-9]+|[.][0-9]+|[01][.]0*|[01])\s*\)$/gm;
        l = jf(bs(e, s), vs(o, u), !0);
      } else a === "#" && (l = Zy(bs(e, s), a + o));
      l && t.push(l);
    }
  return t;
}
function tb(e) {
  return !e || typeof e.getValue != "function" || typeof e.positionAt != "function" ? [] : eb(e);
}
const nb = /^-+|-+$/g, Uf = 100, rb = 5;
function sb(e, t) {
  let n = [];
  if (t.findRegionSectionHeaders && t.foldingRules?.markers) {
    const r = ib(e, t);
    n = n.concat(r);
  }
  if (t.findMarkSectionHeaders) {
    const r = ab(e, t);
    n = n.concat(r);
  }
  return n;
}
function ib(e, t) {
  const n = [], r = e.getLineCount();
  for (let s = 1; s <= r; s++) {
    const i = e.getLineContent(s), a = i.match(t.foldingRules.markers.start);
    if (a) {
      const o = { startLineNumber: s, startColumn: a[0].length + 1, endLineNumber: s, endColumn: i.length + 1 };
      if (o.endColumn > o.startColumn) {
        const l = {
          range: o,
          ...ob(i.substring(a[0].length)),
          shouldBeInComments: !1
        };
        (l.text || l.hasSeparatorLine) && n.push(l);
      }
    }
  }
  return n;
}
function ab(e, t) {
  const n = [], r = e.getLineCount();
  if (!t.markSectionHeaderRegex || t.markSectionHeaderRegex.trim() === "")
    return n;
  const s = oy(t.markSectionHeaderRegex), i = new RegExp(t.markSectionHeaderRegex, `gdm${s ? "s" : ""}`);
  if (n0(i))
    return n;
  for (let a = 1; a <= r; a += Uf - rb) {
    const o = Math.min(a + Uf - 1, r), l = [];
    for (let c = a; c <= o; c++)
      l.push(e.getLineContent(c));
    const u = l.join(`
`);
    i.lastIndex = 0;
    let f;
    for (; (f = i.exec(u)) !== null; ) {
      const c = u.substring(0, f.index), d = (c.match(/\n/g) || []).length, v = a + d, D = f[0].split(`
`), S = D.length, x = v + S - 1, N = c.lastIndexOf(`
`) + 1, k = f.index - N + 1, y = D[D.length - 1], b = S === 1 ? k + f[0].length : y.length + 1, h = {
        startLineNumber: v,
        startColumn: k,
        endLineNumber: x,
        endColumn: b
      }, m = (f.groups ?? {}).label ?? "", p = ((f.groups ?? {}).separator ?? "") !== "", E = {
        range: h,
        text: m,
        hasSeparatorLine: p,
        shouldBeInComments: !0
      };
      (E.text || E.hasSeparatorLine) && (n.length === 0 || n[n.length - 1].range.endLineNumber < E.range.startLineNumber) && n.push(E), i.lastIndex = f.index + f[0].length;
    }
  }
  return n;
}
function ob(e) {
  e = e.trim();
  const t = e.startsWith("-");
  return e = e.replace(nb, ""), { text: e, hasSeparatorLine: t };
}
class lb {
  get isRejected() {
    return this.outcome?.outcome === 1;
  }
  get isSettled() {
    return !!this.outcome;
  }
  constructor() {
    this.p = new Promise((t, n) => {
      this.completeCallback = t, this.errorCallback = n;
    });
  }
  complete(t) {
    return this.isSettled ? Promise.resolve() : new Promise((n) => {
      this.completeCallback(t), this.outcome = { outcome: 0, value: t }, n();
    });
  }
  error(t) {
    return this.isSettled ? Promise.resolve() : new Promise((n) => {
      this.errorCallback(t), this.outcome = { outcome: 1, value: t }, n();
    });
  }
  cancel() {
    return this.error(new t1());
  }
}
var qf;
(function(e) {
  async function t(r) {
    let s;
    const i = await Promise.all(r.map((a) => a.then((o) => o, (o) => {
      s || (s = o);
    })));
    if (typeof s < "u")
      throw s;
    return i;
  }
  e.settled = t;
  function n(r) {
    return new Promise(async (s, i) => {
      try {
        await r(s, i);
      } catch (a) {
        i(a);
      }
    });
  }
  e.withAsyncBody = n;
})(qf || (qf = {}));
class ub {
  constructor() {
    this._unsatisfiedConsumers = [], this._unconsumedValues = [];
  }
  get hasFinalValue() {
    return !!this._finalValue;
  }
  produce(t) {
    if (this._ensureNoFinalValue(), this._unsatisfiedConsumers.length > 0) {
      const n = this._unsatisfiedConsumers.shift();
      this._resolveOrRejectDeferred(n, t);
    } else
      this._unconsumedValues.push(t);
  }
  produceFinal(t) {
    this._ensureNoFinalValue(), this._finalValue = t;
    for (const n of this._unsatisfiedConsumers)
      this._resolveOrRejectDeferred(n, t);
    this._unsatisfiedConsumers.length = 0;
  }
  _ensureNoFinalValue() {
    if (this._finalValue)
      throw new Ge("ProducerConsumer: cannot produce after final value has been set");
  }
  _resolveOrRejectDeferred(t, n) {
    n.ok ? t.complete(n.value) : t.error(n.error);
  }
  consume() {
    if (this._unconsumedValues.length > 0 || this._finalValue) {
      const t = this._unconsumedValues.length > 0 ? this._unconsumedValues.shift() : this._finalValue;
      return t.ok ? Promise.resolve(t.value) : Promise.reject(t.error);
    } else {
      const t = new lb();
      return this._unsatisfiedConsumers.push(t), t.p;
    }
  }
}
const at = class at {
  constructor(t, n) {
    this._onReturn = n, this._producerConsumer = new ub(), this._iterator = {
      next: () => this._producerConsumer.consume(),
      return: () => (this._onReturn?.(), Promise.resolve({ done: !0, value: void 0 })),
      throw: async (r) => (this._finishError(r), { done: !0, value: void 0 })
    }, queueMicrotask(async () => {
      const r = t({
        emitOne: (s) => this._producerConsumer.produce({ ok: !0, value: { done: !1, value: s } }),
        emitMany: (s) => {
          for (const i of s)
            this._producerConsumer.produce({ ok: !0, value: { done: !1, value: i } });
        },
        reject: (s) => this._finishError(s)
      });
      if (!this._producerConsumer.hasFinalValue)
        try {
          await r, this._finishOk();
        } catch (s) {
          this._finishError(s);
        }
    });
  }
  static fromArray(t) {
    return new at((n) => {
      n.emitMany(t);
    });
  }
  static fromPromise(t) {
    return new at(async (n) => {
      n.emitMany(await t);
    });
  }
  static fromPromisesResolveOrder(t) {
    return new at(async (n) => {
      await Promise.all(t.map(async (r) => n.emitOne(await r)));
    });
  }
  static merge(t) {
    return new at(async (n) => {
      await Promise.all(t.map(async (r) => {
        for await (const s of r)
          n.emitOne(s);
      }));
    });
  }
  static map(t, n) {
    return new at(async (r) => {
      for await (const s of t)
        r.emitOne(n(s));
    });
  }
  map(t) {
    return at.map(this, t);
  }
  static coalesce(t) {
    return at.filter(t, (n) => !!n);
  }
  coalesce() {
    return at.coalesce(this);
  }
  static filter(t, n) {
    return new at(async (r) => {
      for await (const s of t)
        n(s) && r.emitOne(s);
    });
  }
  filter(t) {
    return at.filter(this, t);
  }
  _finishOk() {
    this._producerConsumer.hasFinalValue || this._producerConsumer.produceFinal({ ok: !0, value: { done: !0, value: void 0 } });
  }
  _finishError(t) {
    this._producerConsumer.hasFinalValue || this._producerConsumer.produceFinal({ ok: !1, error: t });
  }
  [Symbol.asyncIterator]() {
    return this._iterator;
  }
};
at.EMPTY = at.fromArray([]);
let Wf = at;
class cb {
  constructor(t) {
    this.values = t, this.prefixSum = new Uint32Array(t.length), this.prefixSumValidIndex = new Int32Array(1), this.prefixSumValidIndex[0] = -1;
  }
  insertValues(t, n) {
    t = Dr(t);
    const r = this.values, s = this.prefixSum, i = n.length;
    return i === 0 ? !1 : (this.values = new Uint32Array(r.length + i), this.values.set(r.subarray(0, t), 0), this.values.set(r.subarray(t), t + i), this.values.set(n, t), t - 1 < this.prefixSumValidIndex[0] && (this.prefixSumValidIndex[0] = t - 1), this.prefixSum = new Uint32Array(this.values.length), this.prefixSumValidIndex[0] >= 0 && this.prefixSum.set(s.subarray(0, this.prefixSumValidIndex[0] + 1)), !0);
  }
  setValue(t, n) {
    return t = Dr(t), n = Dr(n), this.values[t] === n ? !1 : (this.values[t] = n, t - 1 < this.prefixSumValidIndex[0] && (this.prefixSumValidIndex[0] = t - 1), !0);
  }
  removeValues(t, n) {
    t = Dr(t), n = Dr(n);
    const r = this.values, s = this.prefixSum;
    if (t >= r.length)
      return !1;
    const i = r.length - t;
    return n >= i && (n = i), n === 0 ? !1 : (this.values = new Uint32Array(r.length - n), this.values.set(r.subarray(0, t), 0), this.values.set(r.subarray(t + n), t), this.prefixSum = new Uint32Array(this.values.length), t - 1 < this.prefixSumValidIndex[0] && (this.prefixSumValidIndex[0] = t - 1), this.prefixSumValidIndex[0] >= 0 && this.prefixSum.set(s.subarray(0, this.prefixSumValidIndex[0] + 1)), !0);
  }
  getTotalSum() {
    return this.values.length === 0 ? 0 : this._getPrefixSum(this.values.length - 1);
  }
  /**
   * Returns the sum of the first `index + 1` many items.
   * @returns `SUM(0 <= j <= index, values[j])`.
   */
  getPrefixSum(t) {
    return t < 0 ? 0 : (t = Dr(t), this._getPrefixSum(t));
  }
  _getPrefixSum(t) {
    if (t <= this.prefixSumValidIndex[0])
      return this.prefixSum[t];
    let n = this.prefixSumValidIndex[0] + 1;
    n === 0 && (this.prefixSum[0] = this.values[0], n++), t >= this.values.length && (t = this.values.length - 1);
    for (let r = n; r <= t; r++)
      this.prefixSum[r] = this.prefixSum[r - 1] + this.values[r];
    return this.prefixSumValidIndex[0] = Math.max(this.prefixSumValidIndex[0], t), this.prefixSum[t];
  }
  getIndexOf(t) {
    t = Math.floor(t), this.getTotalSum();
    let n = 0, r = this.values.length - 1, s = 0, i = 0, a = 0;
    for (; n <= r; )
      if (s = n + (r - n) / 2 | 0, i = this.prefixSum[s], a = i - this.values[s], t < a)
        r = s - 1;
      else if (t >= i)
        n = s + 1;
      else
        break;
    return new fb(s, t - a);
  }
}
class fb {
  constructor(t, n) {
    this.index = t, this.remainder = n, this._prefixSumIndexOfResultBrand = void 0, this.index = t, this.remainder = n;
  }
}
class hb {
  constructor(t, n, r, s) {
    this._uri = t, this._lines = n, this._eol = r, this._versionId = s, this._lineStarts = null, this._cachedTextValue = null;
  }
  dispose() {
    this._lines.length = 0;
  }
  get version() {
    return this._versionId;
  }
  getText() {
    return this._cachedTextValue === null && (this._cachedTextValue = this._lines.join(this._eol)), this._cachedTextValue;
  }
  onEvents(t) {
    t.eol && t.eol !== this._eol && (this._eol = t.eol, this._lineStarts = null);
    const n = t.changes;
    for (const r of n)
      this._acceptDeleteRange(r.range), this._acceptInsertText(new Ne(r.range.startLineNumber, r.range.startColumn), r.text);
    this._versionId = t.versionId, this._cachedTextValue = null;
  }
  _ensureLineStarts() {
    if (!this._lineStarts) {
      const t = this._eol.length, n = this._lines.length, r = new Uint32Array(n);
      for (let s = 0; s < n; s++)
        r[s] = this._lines[s].length + t;
      this._lineStarts = new cb(r);
    }
  }
  /**
   * All changes to a line's text go through this method
   */
  _setLineText(t, n) {
    this._lines[t] = n, this._lineStarts && this._lineStarts.setValue(t, this._lines[t].length + this._eol.length);
  }
  _acceptDeleteRange(t) {
    if (t.startLineNumber === t.endLineNumber) {
      if (t.startColumn === t.endColumn)
        return;
      this._setLineText(t.startLineNumber - 1, this._lines[t.startLineNumber - 1].substring(0, t.startColumn - 1) + this._lines[t.startLineNumber - 1].substring(t.endColumn - 1));
      return;
    }
    this._setLineText(t.startLineNumber - 1, this._lines[t.startLineNumber - 1].substring(0, t.startColumn - 1) + this._lines[t.endLineNumber - 1].substring(t.endColumn - 1)), this._lines.splice(t.startLineNumber, t.endLineNumber - t.startLineNumber), this._lineStarts && this._lineStarts.removeValues(t.startLineNumber, t.endLineNumber - t.startLineNumber);
  }
  _acceptInsertText(t, n) {
    if (n.length === 0)
      return;
    const r = r0(n);
    if (r.length === 1) {
      this._setLineText(t.lineNumber - 1, this._lines[t.lineNumber - 1].substring(0, t.column - 1) + r[0] + this._lines[t.lineNumber - 1].substring(t.column - 1));
      return;
    }
    r[r.length - 1] += this._lines[t.lineNumber - 1].substring(t.column - 1), this._setLineText(t.lineNumber - 1, this._lines[t.lineNumber - 1].substring(0, t.column - 1) + r[0]);
    const s = new Uint32Array(r.length - 1);
    for (let i = 1; i < r.length; i++)
      this._lines.splice(t.lineNumber + i - 1, 0, r[i]), s[i - 1] = r[i].length + this._eol.length;
    this._lineStarts && this._lineStarts.insertValues(t.lineNumber, s);
  }
}
class db {
  constructor() {
    this._models = /* @__PURE__ */ Object.create(null);
  }
  getModel(t) {
    return this._models[t];
  }
  getModels() {
    const t = [];
    return Object.keys(this._models).forEach((n) => t.push(this._models[n])), t;
  }
  $acceptNewModel(t) {
    this._models[t.url] = new mb(su.parse(t.url), t.lines, t.EOL, t.versionId);
  }
  $acceptModelChanged(t, n) {
    if (!this._models[t])
      return;
    this._models[t].onEvents(n);
  }
  $acceptRemovedModel(t) {
    this._models[t] && delete this._models[t];
  }
}
class mb extends hb {
  get uri() {
    return this._uri;
  }
  get eol() {
    return this._eol;
  }
  getValue() {
    return this.getText();
  }
  findMatches(t) {
    const n = [];
    for (let r = 0; r < this._lines.length; r++) {
      const s = this._lines[r], i = this.offsetAt(new Ne(r + 1, 1)), a = s.matchAll(t);
      for (const o of a)
        (o.index || o.index === 0) && (o.index = o.index + i), n.push(o);
    }
    return n;
  }
  getLinesContent() {
    return this._lines.slice(0);
  }
  getLineCount() {
    return this._lines.length;
  }
  getLineContent(t) {
    return this._lines[t - 1];
  }
  getWordAtPosition(t, n) {
    const r = iu(t.column, p1(n), this._lines[t.lineNumber - 1], 0);
    return r ? new fe(t.lineNumber, r.startColumn, t.lineNumber, r.endColumn) : null;
  }
  words(t) {
    const n = this._lines, r = this._wordenize.bind(this);
    let s = 0, i = "", a = 0, o = [];
    return {
      *[Symbol.iterator]() {
        for (; ; )
          if (a < o.length) {
            const l = i.substring(o[a].start, o[a].end);
            a += 1, yield l;
          } else if (s < n.length)
            i = n[s], o = r(i, t), a = 0, s += 1;
          else
            break;
      }
    };
  }
  getLineWords(t, n) {
    const r = this._lines[t - 1], s = this._wordenize(r, n), i = [];
    for (const a of s)
      i.push({
        word: r.substring(a.start, a.end),
        startColumn: a.start + 1,
        endColumn: a.end + 1
      });
    return i;
  }
  _wordenize(t, n) {
    const r = [];
    let s;
    for (n.lastIndex = 0; (s = n.exec(t)) && s[0].length !== 0; )
      r.push({ start: s.index, end: s.index + s[0].length });
    return r;
  }
  getValueInRange(t) {
    if (t = this._validateRange(t), t.startLineNumber === t.endLineNumber)
      return this._lines[t.startLineNumber - 1].substring(t.startColumn - 1, t.endColumn - 1);
    const n = this._eol, r = t.startLineNumber - 1, s = t.endLineNumber - 1, i = [];
    i.push(this._lines[r].substring(t.startColumn - 1));
    for (let a = r + 1; a < s; a++)
      i.push(this._lines[a]);
    return i.push(this._lines[s].substring(0, t.endColumn - 1)), i.join(n);
  }
  offsetAt(t) {
    return t = this._validatePosition(t), this._ensureLineStarts(), this._lineStarts.getPrefixSum(t.lineNumber - 2) + (t.column - 1);
  }
  positionAt(t) {
    t = Math.floor(t), t = Math.max(0, t), this._ensureLineStarts();
    const n = this._lineStarts.getIndexOf(t), r = this._lines[n.index].length;
    return {
      lineNumber: 1 + n.index,
      column: 1 + Math.min(n.remainder, r)
    };
  }
  _validateRange(t) {
    const n = this._validatePosition({ lineNumber: t.startLineNumber, column: t.startColumn }), r = this._validatePosition({ lineNumber: t.endLineNumber, column: t.endColumn });
    return n.lineNumber !== t.startLineNumber || n.column !== t.startColumn || r.lineNumber !== t.endLineNumber || r.column !== t.endColumn ? {
      startLineNumber: n.lineNumber,
      startColumn: n.column,
      endLineNumber: r.lineNumber,
      endColumn: r.column
    } : t;
  }
  _validatePosition(t) {
    if (!Ne.isIPosition(t))
      throw new Error("bad position");
    let { lineNumber: n, column: r } = t, s = !1;
    if (n < 1)
      n = 1, r = 1, s = !0;
    else if (n > this._lines.length)
      n = this._lines.length, r = this._lines[n - 1].length + 1, s = !0;
    else {
      const i = this._lines[n - 1].length + 1;
      r < 1 ? (r = 1, s = !0) : r > i && (r = i, s = !0);
    }
    return s ? { lineNumber: n, column: r } : t;
  }
}
const Qn = class Qn {
  constructor(t = null) {
    this._foreignModule = t, this._workerTextModelSyncServer = new db();
  }
  dispose() {
  }
  async $ping() {
    return "pong";
  }
  _getModel(t) {
    return this._workerTextModelSyncServer.getModel(t);
  }
  getModels() {
    return this._workerTextModelSyncServer.getModels();
  }
  $acceptNewModel(t) {
    this._workerTextModelSyncServer.$acceptNewModel(t);
  }
  $acceptModelChanged(t, n) {
    this._workerTextModelSyncServer.$acceptModelChanged(t, n);
  }
  $acceptRemovedModel(t) {
    this._workerTextModelSyncServer.$acceptRemovedModel(t);
  }
  async $computeUnicodeHighlights(t, n, r) {
    const s = this._getModel(t);
    return s ? py.computeUnicodeHighlights(s, n, r) : { ranges: [], hasMore: !1, ambiguousCharacterCount: 0, invisibleCharacterCount: 0, nonBasicAsciiCharacterCount: 0 };
  }
  async $findSectionHeaders(t, n) {
    const r = this._getModel(t);
    return r ? sb(r, n) : [];
  }
  // ---- BEGIN diff --------------------------------------------------------------------------
  async $computeDiff(t, n, r, s) {
    const i = this._getModel(t), a = this._getModel(n);
    return !i || !a ? null : Qn.computeDiff(i, a, r, s);
  }
  static computeDiff(t, n, r, s) {
    const i = s === "advanced" ? Bf.getDefault() : Bf.getLegacy(), a = t.getLinesContent(), o = n.getLinesContent(), l = i.computeDiff(a, o, r), u = l.changes.length > 0 ? !1 : this._modelsAreIdentical(t, n);
    function f(c) {
      return c.map((d) => [d.original.startLineNumber, d.original.endLineNumberExclusive, d.modified.startLineNumber, d.modified.endLineNumberExclusive, d.innerChanges?.map((v) => [
        v.originalRange.startLineNumber,
        v.originalRange.startColumn,
        v.originalRange.endLineNumber,
        v.originalRange.endColumn,
        v.modifiedRange.startLineNumber,
        v.modifiedRange.startColumn,
        v.modifiedRange.endLineNumber,
        v.modifiedRange.endColumn
      ])]);
    }
    return {
      identical: u,
      quitEarly: l.hitTimeout,
      changes: f(l.changes),
      moves: l.moves.map((c) => [
        c.lineRangeMapping.original.startLineNumber,
        c.lineRangeMapping.original.endLineNumberExclusive,
        c.lineRangeMapping.modified.startLineNumber,
        c.lineRangeMapping.modified.endLineNumberExclusive,
        f(c.changes)
      ])
    };
  }
  static _modelsAreIdentical(t, n) {
    const r = t.getLineCount(), s = n.getLineCount();
    if (r !== s)
      return !1;
    for (let i = 1; i <= r; i++) {
      const a = t.getLineContent(i), o = n.getLineContent(i);
      if (a !== o)
        return !1;
    }
    return !0;
  }
  async $computeMoreMinimalEdits(t, n, r) {
    const s = this._getModel(t);
    if (!s)
      return n;
    const i = [];
    let a;
    n = n.slice(0).sort((l, u) => {
      if (l.range && u.range)
        return fe.compareRangesUsingStarts(l.range, u.range);
      const f = l.range ? 0 : 1, c = u.range ? 0 : 1;
      return f - c;
    });
    let o = 0;
    for (let l = 1; l < n.length; l++)
      fe.getEndPosition(n[o].range).equals(fe.getStartPosition(n[l].range)) ? (n[o].range = fe.fromPositions(fe.getStartPosition(n[o].range), fe.getEndPosition(n[l].range)), n[o].text += n[l].text) : (o++, n[o] = n[l]);
    n.length = o + 1;
    for (let { range: l, text: u, eol: f } of n) {
      if (typeof f == "number" && (a = f), fe.isEmpty(l) && !u)
        continue;
      const c = s.getValueInRange(l);
      if (u = u.replace(/\r\n|\n|\r/g, s.eol), c === u)
        continue;
      if (Math.max(u.length, c.length) > Qn._diffLimit) {
        i.push({ range: l, text: u });
        continue;
      }
      const d = S0(c, u, r), v = s.offsetAt(fe.lift(l).getStartPosition());
      for (const D of d) {
        const S = s.positionAt(v + D.originalStart), x = s.positionAt(v + D.originalStart + D.originalLength), N = {
          text: u.substr(D.modifiedStart, D.modifiedLength),
          range: { startLineNumber: S.lineNumber, startColumn: S.column, endLineNumber: x.lineNumber, endColumn: x.column }
        };
        s.getValueInRange(N.range) !== N.text && i.push(N);
      }
    }
    return typeof a == "number" && i.push({ eol: a, text: "", range: { startLineNumber: 0, startColumn: 0, endLineNumber: 0, endColumn: 0 } }), i;
  }
  // ---- END minimal edits ---------------------------------------------------------------
  async $computeLinks(t) {
    const n = this._getModel(t);
    return n ? L0(n) : null;
  }
  // --- BEGIN default document colors -----------------------------------------------------------
  async $computeDefaultDocumentColors(t) {
    const n = this._getModel(t);
    return n ? tb(n) : null;
  }
  async $textualSuggest(t, n, r, s) {
    const i = new Aa(), a = new RegExp(r, s), o = /* @__PURE__ */ new Set();
    e: for (const l of t) {
      const u = this._getModel(l);
      if (u) {
        for (const f of u.words(a))
          if (!(f === n || !isNaN(Number(f))) && (o.add(f), o.size > Qn._suggestionsLimit))
            break e;
      }
    }
    return { words: Array.from(o), duration: i.elapsed() };
  }
  // ---- END suggest --------------------------------------------------------------------------
  //#region -- word ranges --
  async $computeWordRanges(t, n, r, s) {
    const i = this._getModel(t);
    if (!i)
      return /* @__PURE__ */ Object.create(null);
    const a = new RegExp(r, s), o = /* @__PURE__ */ Object.create(null);
    for (let l = n.startLineNumber; l < n.endLineNumber; l++) {
      const u = i.getLineWords(l, a);
      for (const f of u) {
        if (!isNaN(Number(f.word)))
          continue;
        let c = o[f.word];
        c || (c = [], o[f.word] = c), c.push({
          startLineNumber: l,
          startColumn: f.startColumn,
          endLineNumber: l,
          endColumn: f.endColumn
        });
      }
    }
    return o;
  }
  //#endregion
  async $navigateValueSet(t, n, r, s, i) {
    const a = this._getModel(t);
    if (!a)
      return null;
    const o = new RegExp(s, i);
    n.startColumn === n.endColumn && (n = {
      startLineNumber: n.startLineNumber,
      startColumn: n.startColumn,
      endLineNumber: n.endLineNumber,
      endColumn: n.endColumn + 1
    });
    const l = a.getValueInRange(n), u = a.getWordAtPosition({ lineNumber: n.startLineNumber, column: n.startColumn }, o);
    if (!u)
      return null;
    const f = a.getValueInRange(u);
    return Oo.INSTANCE.navigateValueSet(n, l, u, f, r);
  }
  // ---- BEGIN foreign module support --------------------------------------------------------------------------
  // foreign method request
  $fmr(t, n) {
    if (!this._foreignModule || typeof this._foreignModule[t] != "function")
      return Promise.reject(new Error("Missing requestHandler or method: " + t));
    try {
      return Promise.resolve(this._foreignModule[t].apply(this._foreignModule, n));
    } catch (r) {
      return Promise.reject(r);
    }
  }
};
Qn._diffLimit = 1e5, Qn._suggestionsLimit = 1e4;
let Qo = Qn;
typeof importScripts == "function" && (globalThis.monaco = ny());
const Ws = class Ws {
  static getChannel(t) {
    return t.getChannel(Ws.CHANNEL_NAME);
  }
  static setChannel(t, n) {
    t.setChannel(Ws.CHANNEL_NAME, n);
  }
};
Ws.CHANNEL_NAME = "editorWorkerHost";
let Ko = Ws;
function w1(e) {
  let t;
  const n = w0((r) => {
    const s = Ko.getChannel(r), a = {
      host: new Proxy({}, {
        get(o, l, u) {
          if (l !== "then") {
            if (typeof l != "string")
              throw new Error("Not supported");
            return (...f) => s.$fhr(l, f);
          }
        }
      }),
      getMirrorModels: () => n.requestHandler.getModels()
    };
    return t = e(a), new Qo(t);
  });
  return t;
}
var D1 = !1;
function pb() {
  return D1;
}
function gb(e) {
  D1 = !0, self.onmessage = (t) => {
    w1((n) => e(n, t.data));
  };
}
self.onmessage = () => {
  pb() || w1(() => ({}));
};
function yb(e) {
  self.onmessage = () => {
    gb((t, n) => Object.create(e(t, n)));
  };
}
let Hf = class Xo {
  constructor(t, n, r, s) {
    this._uri = t, this._languageId = n, this._version = r, this._content = s, this._lineOffsets = void 0;
  }
  get uri() {
    return this._uri;
  }
  get languageId() {
    return this._languageId;
  }
  get version() {
    return this._version;
  }
  getText(t) {
    if (t) {
      const n = this.offsetAt(t.start), r = this.offsetAt(t.end);
      return this._content.substring(n, r);
    }
    return this._content;
  }
  update(t, n) {
    for (const r of t)
      if (Xo.isIncremental(r)) {
        const s = E1(r.range), i = this.offsetAt(s.start), a = this.offsetAt(s.end);
        this._content = this._content.substring(0, i) + r.text + this._content.substring(a, this._content.length);
        const o = Math.max(s.start.line, 0), l = Math.max(s.end.line, 0);
        let u = this._lineOffsets;
        const f = Yf(r.text, !1, i);
        if (l - o === f.length)
          for (let d = 0, v = f.length; d < v; d++)
            u[d + o + 1] = f[d];
        else
          f.length < 1e4 ? u.splice(o + 1, l - o, ...f) : this._lineOffsets = u = u.slice(0, o + 1).concat(f, u.slice(l + 1));
        const c = r.text.length - (a - i);
        if (c !== 0)
          for (let d = o + 1 + f.length, v = u.length; d < v; d++)
            u[d] = u[d] + c;
      } else if (Xo.isFull(r))
        this._content = r.text, this._lineOffsets = void 0;
      else
        throw new Error("Unknown change event received");
    this._version = n;
  }
  getLineOffsets() {
    return this._lineOffsets === void 0 && (this._lineOffsets = Yf(this._content, !0)), this._lineOffsets;
  }
  positionAt(t) {
    t = Math.max(Math.min(t, this._content.length), 0);
    const n = this.getLineOffsets();
    let r = 0, s = n.length;
    if (s === 0)
      return { line: 0, character: t };
    for (; r < s; ) {
      const a = Math.floor((r + s) / 2);
      n[a] > t ? s = a : r = a + 1;
    }
    const i = r - 1;
    return t = this.ensureBeforeEOL(t, n[i]), { line: i, character: t - n[i] };
  }
  offsetAt(t) {
    const n = this.getLineOffsets();
    if (t.line >= n.length)
      return this._content.length;
    if (t.line < 0)
      return 0;
    const r = n[t.line];
    if (t.character <= 0)
      return r;
    const s = t.line + 1 < n.length ? n[t.line + 1] : this._content.length, i = Math.min(r + t.character, s);
    return this.ensureBeforeEOL(i, r);
  }
  ensureBeforeEOL(t, n) {
    for (; t > n && S1(this._content.charCodeAt(t - 1)); )
      t--;
    return t;
  }
  get lineCount() {
    return this.getLineOffsets().length;
  }
  static isIncremental(t) {
    const n = t;
    return n != null && typeof n.text == "string" && n.range !== void 0 && (n.rangeLength === void 0 || typeof n.rangeLength == "number");
  }
  static isFull(t) {
    const n = t;
    return n != null && typeof n.text == "string" && n.range === void 0 && n.rangeLength === void 0;
  }
};
var Zo;
(function(e) {
  function t(s, i, a, o) {
    return new Hf(s, i, a, o);
  }
  e.create = t;
  function n(s, i, a) {
    if (s instanceof Hf)
      return s.update(i, a), s;
    throw new Error("TextDocument.update: document must be created by TextDocument.create");
  }
  e.update = n;
  function r(s, i) {
    const a = s.getText(), o = el(i.map(bb), (f, c) => {
      const d = f.range.start.line - c.range.start.line;
      return d === 0 ? f.range.start.character - c.range.start.character : d;
    });
    let l = 0;
    const u = [];
    for (const f of o) {
      const c = s.offsetAt(f.range.start);
      if (c < l)
        throw new Error("Overlapping edit");
      c > l && u.push(a.substring(l, c)), f.newText.length && u.push(f.newText), l = s.offsetAt(f.range.end);
    }
    return u.push(a.substr(l)), u.join("");
  }
  e.applyEdits = r;
})(Zo || (Zo = {}));
function el(e, t) {
  if (e.length <= 1)
    return e;
  const n = e.length / 2 | 0, r = e.slice(0, n), s = e.slice(n);
  el(r, t), el(s, t);
  let i = 0, a = 0, o = 0;
  for (; i < r.length && a < s.length; )
    t(r[i], s[a]) <= 0 ? e[o++] = r[i++] : e[o++] = s[a++];
  for (; i < r.length; )
    e[o++] = r[i++];
  for (; a < s.length; )
    e[o++] = s[a++];
  return e;
}
function Yf(e, t, n = 0) {
  const r = t ? [n] : [];
  for (let s = 0; s < e.length; s++) {
    const i = e.charCodeAt(s);
    S1(i) && (i === 13 && s + 1 < e.length && e.charCodeAt(s + 1) === 10 && s++, r.push(n + s + 1));
  }
  return r;
}
function S1(e) {
  return e === 13 || e === 10;
}
function E1(e) {
  const t = e.start, n = e.end;
  return t.line > n.line || t.line === n.line && t.character > n.character ? { start: n, end: t } : e;
}
function bb(e) {
  const t = E1(e.range);
  return t !== e.range ? { newText: e.newText, range: t } : e;
}
function vb(e, t = !1) {
  const n = e.length;
  let r = 0, s = "", i = 0, a = 16, o = 0, l = 0, u = 0, f = 0, c = 0;
  function d(y, b) {
    let h = 0, m = 0;
    for (; h < y; ) {
      let p = e.charCodeAt(r);
      if (p >= 48 && p <= 57)
        m = m * 16 + p - 48;
      else if (p >= 65 && p <= 70)
        m = m * 16 + p - 65 + 10;
      else if (p >= 97 && p <= 102)
        m = m * 16 + p - 97 + 10;
      else
        break;
      r++, h++;
    }
    return h < y && (m = -1), m;
  }
  function v(y) {
    r = y, s = "", i = 0, a = 16, c = 0;
  }
  function D() {
    let y = r;
    if (e.charCodeAt(r) === 48)
      r++;
    else
      for (r++; r < e.length && xr(e.charCodeAt(r)); )
        r++;
    if (r < e.length && e.charCodeAt(r) === 46)
      if (r++, r < e.length && xr(e.charCodeAt(r)))
        for (r++; r < e.length && xr(e.charCodeAt(r)); )
          r++;
      else
        return c = 3, e.substring(y, r);
    let b = r;
    if (r < e.length && (e.charCodeAt(r) === 69 || e.charCodeAt(r) === 101))
      if (r++, (r < e.length && e.charCodeAt(r) === 43 || e.charCodeAt(r) === 45) && r++, r < e.length && xr(e.charCodeAt(r))) {
        for (r++; r < e.length && xr(e.charCodeAt(r)); )
          r++;
        b = r;
      } else
        c = 3;
    return e.substring(y, b);
  }
  function S() {
    let y = "", b = r;
    for (; ; ) {
      if (r >= n) {
        y += e.substring(b, r), c = 2;
        break;
      }
      const h = e.charCodeAt(r);
      if (h === 34) {
        y += e.substring(b, r), r++;
        break;
      }
      if (h === 92) {
        if (y += e.substring(b, r), r++, r >= n) {
          c = 2;
          break;
        }
        switch (e.charCodeAt(r++)) {
          case 34:
            y += '"';
            break;
          case 92:
            y += "\\";
            break;
          case 47:
            y += "/";
            break;
          case 98:
            y += "\b";
            break;
          case 102:
            y += "\f";
            break;
          case 110:
            y += `
`;
            break;
          case 114:
            y += "\r";
            break;
          case 116:
            y += "	";
            break;
          case 117:
            const p = d(4);
            p >= 0 ? y += String.fromCharCode(p) : c = 4;
            break;
          default:
            c = 5;
        }
        b = r;
        continue;
      }
      if (h >= 0 && h <= 31)
        if (ws(h)) {
          y += e.substring(b, r), c = 2;
          break;
        } else
          c = 6;
      r++;
    }
    return y;
  }
  function x() {
    if (s = "", c = 0, i = r, l = o, f = u, r >= n)
      return i = n, a = 17;
    let y = e.charCodeAt(r);
    if (Za(y)) {
      do
        r++, s += String.fromCharCode(y), y = e.charCodeAt(r);
      while (Za(y));
      return a = 15;
    }
    if (ws(y))
      return r++, s += String.fromCharCode(y), y === 13 && e.charCodeAt(r) === 10 && (r++, s += `
`), o++, u = r, a = 14;
    switch (y) {
      // tokens: []{}:,
      case 123:
        return r++, a = 1;
      case 125:
        return r++, a = 2;
      case 91:
        return r++, a = 3;
      case 93:
        return r++, a = 4;
      case 58:
        return r++, a = 6;
      case 44:
        return r++, a = 5;
      // strings
      case 34:
        return r++, s = S(), a = 10;
      // comments
      case 47:
        const b = r - 1;
        if (e.charCodeAt(r + 1) === 47) {
          for (r += 2; r < n && !ws(e.charCodeAt(r)); )
            r++;
          return s = e.substring(b, r), a = 12;
        }
        if (e.charCodeAt(r + 1) === 42) {
          r += 2;
          const h = n - 1;
          let m = !1;
          for (; r < h; ) {
            const p = e.charCodeAt(r);
            if (p === 42 && e.charCodeAt(r + 1) === 47) {
              r += 2, m = !0;
              break;
            }
            r++, ws(p) && (p === 13 && e.charCodeAt(r) === 10 && r++, o++, u = r);
          }
          return m || (r++, c = 1), s = e.substring(b, r), a = 13;
        }
        return s += String.fromCharCode(y), r++, a = 16;
      // numbers
      case 45:
        if (s += String.fromCharCode(y), r++, r === n || !xr(e.charCodeAt(r)))
          return a = 16;
      // found a minus, followed by a number so
      // we fall through to proceed with scanning
      // numbers
      case 48:
      case 49:
      case 50:
      case 51:
      case 52:
      case 53:
      case 54:
      case 55:
      case 56:
      case 57:
        return s += D(), a = 11;
      // literals and unknown symbols
      default:
        for (; r < n && N(y); )
          r++, y = e.charCodeAt(r);
        if (i !== r) {
          switch (s = e.substring(i, r), s) {
            case "true":
              return a = 8;
            case "false":
              return a = 9;
            case "null":
              return a = 7;
          }
          return a = 16;
        }
        return s += String.fromCharCode(y), r++, a = 16;
    }
  }
  function N(y) {
    if (Za(y) || ws(y))
      return !1;
    switch (y) {
      case 125:
      case 93:
      case 123:
      case 91:
      case 34:
      case 58:
      case 44:
      case 47:
        return !1;
    }
    return !0;
  }
  function k() {
    let y;
    do
      y = x();
    while (y >= 12 && y <= 15);
    return y;
  }
  return {
    setPosition: v,
    getPosition: () => r,
    scan: t ? k : x,
    getToken: () => a,
    getTokenValue: () => s,
    getTokenOffset: () => i,
    getTokenLength: () => r - i,
    getTokenStartLine: () => l,
    getTokenStartCharacter: () => i - f,
    getTokenError: () => c
  };
}
function Za(e) {
  return e === 32 || e === 9;
}
function ws(e) {
  return e === 10 || e === 13;
}
function xr(e) {
  return e >= 48 && e <= 57;
}
var zf;
(function(e) {
  e[e.lineFeed = 10] = "lineFeed", e[e.carriageReturn = 13] = "carriageReturn", e[e.space = 32] = "space", e[e._0 = 48] = "_0", e[e._1 = 49] = "_1", e[e._2 = 50] = "_2", e[e._3 = 51] = "_3", e[e._4 = 52] = "_4", e[e._5 = 53] = "_5", e[e._6 = 54] = "_6", e[e._7 = 55] = "_7", e[e._8 = 56] = "_8", e[e._9 = 57] = "_9", e[e.a = 97] = "a", e[e.b = 98] = "b", e[e.c = 99] = "c", e[e.d = 100] = "d", e[e.e = 101] = "e", e[e.f = 102] = "f", e[e.g = 103] = "g", e[e.h = 104] = "h", e[e.i = 105] = "i", e[e.j = 106] = "j", e[e.k = 107] = "k", e[e.l = 108] = "l", e[e.m = 109] = "m", e[e.n = 110] = "n", e[e.o = 111] = "o", e[e.p = 112] = "p", e[e.q = 113] = "q", e[e.r = 114] = "r", e[e.s = 115] = "s", e[e.t = 116] = "t", e[e.u = 117] = "u", e[e.v = 118] = "v", e[e.w = 119] = "w", e[e.x = 120] = "x", e[e.y = 121] = "y", e[e.z = 122] = "z", e[e.A = 65] = "A", e[e.B = 66] = "B", e[e.C = 67] = "C", e[e.D = 68] = "D", e[e.E = 69] = "E", e[e.F = 70] = "F", e[e.G = 71] = "G", e[e.H = 72] = "H", e[e.I = 73] = "I", e[e.J = 74] = "J", e[e.K = 75] = "K", e[e.L = 76] = "L", e[e.M = 77] = "M", e[e.N = 78] = "N", e[e.O = 79] = "O", e[e.P = 80] = "P", e[e.Q = 81] = "Q", e[e.R = 82] = "R", e[e.S = 83] = "S", e[e.T = 84] = "T", e[e.U = 85] = "U", e[e.V = 86] = "V", e[e.W = 87] = "W", e[e.X = 88] = "X", e[e.Y = 89] = "Y", e[e.Z = 90] = "Z", e[e.asterisk = 42] = "asterisk", e[e.backslash = 92] = "backslash", e[e.closeBrace = 125] = "closeBrace", e[e.closeBracket = 93] = "closeBracket", e[e.colon = 58] = "colon", e[e.comma = 44] = "comma", e[e.dot = 46] = "dot", e[e.doubleQuote = 34] = "doubleQuote", e[e.minus = 45] = "minus", e[e.openBrace = 123] = "openBrace", e[e.openBracket = 91] = "openBracket", e[e.plus = 43] = "plus", e[e.slash = 47] = "slash", e[e.formFeed = 12] = "formFeed", e[e.tab = 9] = "tab";
})(zf || (zf = {}));
new Array(20).fill(0).map((e, t) => " ".repeat(t));
const Nr = 200;
new Array(Nr).fill(0).map((e, t) => `
` + " ".repeat(t)), new Array(Nr).fill(0).map((e, t) => "\r" + " ".repeat(t)), new Array(Nr).fill(0).map((e, t) => `\r
` + " ".repeat(t)), new Array(Nr).fill(0).map((e, t) => `
` + "	".repeat(t)), new Array(Nr).fill(0).map((e, t) => "\r" + "	".repeat(t)), new Array(Nr).fill(0).map((e, t) => `\r
` + "	".repeat(t));
var ta;
(function(e) {
  e.DEFAULT = {
    allowTrailingComma: !1
  };
})(ta || (ta = {}));
function wb(e, t = [], n = ta.DEFAULT) {
  let r = null, s = [];
  const i = [];
  function a(l) {
    Array.isArray(s) ? s.push(l) : r !== null && (s[r] = l);
  }
  return Db(e, {
    onObjectBegin: () => {
      const l = {};
      a(l), i.push(s), s = l, r = null;
    },
    onObjectProperty: (l) => {
      r = l;
    },
    onObjectEnd: () => {
      s = i.pop();
    },
    onArrayBegin: () => {
      const l = [];
      a(l), i.push(s), s = l, r = null;
    },
    onArrayEnd: () => {
      s = i.pop();
    },
    onLiteralValue: a,
    onError: (l, u, f) => {
      t.push({ error: l, offset: u, length: f });
    }
  }, n), s[0];
}
function tl(e) {
  switch (e.type) {
    case "array":
      return e.children.map(tl);
    case "object":
      const t = /* @__PURE__ */ Object.create(null);
      for (let n of e.children) {
        const r = n.children[1];
        r && (t[n.children[0].value] = tl(r));
      }
      return t;
    case "null":
    case "string":
    case "number":
    case "boolean":
      return e.value;
    default:
      return;
  }
}
function Db(e, t, n = ta.DEFAULT) {
  const r = vb(e, !1), s = [];
  let i = 0;
  function a(O) {
    return O ? () => i === 0 && O(r.getTokenOffset(), r.getTokenLength(), r.getTokenStartLine(), r.getTokenStartCharacter()) : () => !0;
  }
  function o(O) {
    return O ? (T) => i === 0 && O(T, r.getTokenOffset(), r.getTokenLength(), r.getTokenStartLine(), r.getTokenStartCharacter()) : () => !0;
  }
  function l(O) {
    return O ? (T) => i === 0 && O(T, r.getTokenOffset(), r.getTokenLength(), r.getTokenStartLine(), r.getTokenStartCharacter(), () => s.slice()) : () => !0;
  }
  function u(O) {
    return O ? () => {
      i > 0 ? i++ : O(r.getTokenOffset(), r.getTokenLength(), r.getTokenStartLine(), r.getTokenStartCharacter(), () => s.slice()) === !1 && (i = 1);
    } : () => !0;
  }
  function f(O) {
    return O ? () => {
      i > 0 && i--, i === 0 && O(r.getTokenOffset(), r.getTokenLength(), r.getTokenStartLine(), r.getTokenStartCharacter());
    } : () => !0;
  }
  const c = u(t.onObjectBegin), d = l(t.onObjectProperty), v = f(t.onObjectEnd), D = u(t.onArrayBegin), S = f(t.onArrayEnd), x = l(t.onLiteralValue), N = o(t.onSeparator), k = a(t.onComment), y = o(t.onError), b = n && n.disallowComments, h = n && n.allowTrailingComma;
  function m() {
    for (; ; ) {
      const O = r.scan();
      switch (r.getTokenError()) {
        case 4:
          p(
            14
            /* ParseErrorCode.InvalidUnicode */
          );
          break;
        case 5:
          p(
            15
            /* ParseErrorCode.InvalidEscapeCharacter */
          );
          break;
        case 3:
          p(
            13
            /* ParseErrorCode.UnexpectedEndOfNumber */
          );
          break;
        case 1:
          b || p(
            11
            /* ParseErrorCode.UnexpectedEndOfComment */
          );
          break;
        case 2:
          p(
            12
            /* ParseErrorCode.UnexpectedEndOfString */
          );
          break;
        case 6:
          p(
            16
            /* ParseErrorCode.InvalidCharacter */
          );
          break;
      }
      switch (O) {
        case 12:
        case 13:
          b ? p(
            10
            /* ParseErrorCode.InvalidCommentToken */
          ) : k();
          break;
        case 16:
          p(
            1
            /* ParseErrorCode.InvalidSymbol */
          );
          break;
        case 15:
        case 14:
          break;
        default:
          return O;
      }
    }
  }
  function p(O, T = [], P = []) {
    if (y(O), T.length + P.length > 0) {
      let V = r.getToken();
      for (; V !== 17; ) {
        if (T.indexOf(V) !== -1) {
          m();
          break;
        } else if (P.indexOf(V) !== -1)
          break;
        V = m();
      }
    }
  }
  function E(O) {
    const T = r.getTokenValue();
    return O ? x(T) : (d(T), s.push(T)), m(), !0;
  }
  function w() {
    switch (r.getToken()) {
      case 11:
        const O = r.getTokenValue();
        let T = Number(O);
        isNaN(T) && (p(
          2
          /* ParseErrorCode.InvalidNumberFormat */
        ), T = 0), x(T);
        break;
      case 7:
        x(null);
        break;
      case 8:
        x(!0);
        break;
      case 9:
        x(!1);
        break;
      default:
        return !1;
    }
    return m(), !0;
  }
  function L() {
    return r.getToken() !== 10 ? (p(3, [], [
      2,
      5
      /* SyntaxKind.CommaToken */
    ]), !1) : (E(!1), r.getToken() === 6 ? (N(":"), m(), _() || p(4, [], [
      2,
      5
      /* SyntaxKind.CommaToken */
    ])) : p(5, [], [
      2,
      5
      /* SyntaxKind.CommaToken */
    ]), s.pop(), !0);
  }
  function C() {
    c(), m();
    let O = !1;
    for (; r.getToken() !== 2 && r.getToken() !== 17; ) {
      if (r.getToken() === 5) {
        if (O || p(4, [], []), N(","), m(), r.getToken() === 2 && h)
          break;
      } else O && p(6, [], []);
      L() || p(4, [], [
        2,
        5
        /* SyntaxKind.CommaToken */
      ]), O = !0;
    }
    return v(), r.getToken() !== 2 ? p(7, [
      2
      /* SyntaxKind.CloseBraceToken */
    ], []) : m(), !0;
  }
  function A() {
    D(), m();
    let O = !0, T = !1;
    for (; r.getToken() !== 4 && r.getToken() !== 17; ) {
      if (r.getToken() === 5) {
        if (T || p(4, [], []), N(","), m(), r.getToken() === 4 && h)
          break;
      } else T && p(6, [], []);
      O ? (s.push(0), O = !1) : s[s.length - 1]++, _() || p(4, [], [
        4,
        5
        /* SyntaxKind.CommaToken */
      ]), T = !0;
    }
    return S(), O || s.pop(), r.getToken() !== 4 ? p(8, [
      4
      /* SyntaxKind.CloseBracketToken */
    ], []) : m(), !0;
  }
  function _() {
    switch (r.getToken()) {
      case 3:
        return A();
      case 1:
        return C();
      case 10:
        return E(!0);
      default:
        return w();
    }
  }
  return m(), r.getToken() === 17 ? n.allowEmptyContent ? !0 : (p(4, [], []), !1) : _() ? (r.getToken() !== 17 && p(9, [], []), !0) : (p(4, [], []), !1);
}
var Gf;
(function(e) {
  e[e.None = 0] = "None", e[e.UnexpectedEndOfComment = 1] = "UnexpectedEndOfComment", e[e.UnexpectedEndOfString = 2] = "UnexpectedEndOfString", e[e.UnexpectedEndOfNumber = 3] = "UnexpectedEndOfNumber", e[e.InvalidUnicode = 4] = "InvalidUnicode", e[e.InvalidEscapeCharacter = 5] = "InvalidEscapeCharacter", e[e.InvalidCharacter = 6] = "InvalidCharacter";
})(Gf || (Gf = {}));
var Jf;
(function(e) {
  e[e.OpenBraceToken = 1] = "OpenBraceToken", e[e.CloseBraceToken = 2] = "CloseBraceToken", e[e.OpenBracketToken = 3] = "OpenBracketToken", e[e.CloseBracketToken = 4] = "CloseBracketToken", e[e.CommaToken = 5] = "CommaToken", e[e.ColonToken = 6] = "ColonToken", e[e.NullKeyword = 7] = "NullKeyword", e[e.TrueKeyword = 8] = "TrueKeyword", e[e.FalseKeyword = 9] = "FalseKeyword", e[e.StringLiteral = 10] = "StringLiteral", e[e.NumericLiteral = 11] = "NumericLiteral", e[e.LineCommentTrivia = 12] = "LineCommentTrivia", e[e.BlockCommentTrivia = 13] = "BlockCommentTrivia", e[e.LineBreakTrivia = 14] = "LineBreakTrivia", e[e.Trivia = 15] = "Trivia", e[e.Unknown = 16] = "Unknown", e[e.EOF = 17] = "EOF";
})(Jf || (Jf = {}));
const Sb = wb, Eb = tl;
var Qf;
(function(e) {
  e[e.InvalidSymbol = 1] = "InvalidSymbol", e[e.InvalidNumberFormat = 2] = "InvalidNumberFormat", e[e.PropertyNameExpected = 3] = "PropertyNameExpected", e[e.ValueExpected = 4] = "ValueExpected", e[e.ColonExpected = 5] = "ColonExpected", e[e.CommaExpected = 6] = "CommaExpected", e[e.CloseBraceExpected = 7] = "CloseBraceExpected", e[e.CloseBracketExpected = 8] = "CloseBracketExpected", e[e.EndOfFileExpected = 9] = "EndOfFileExpected", e[e.InvalidCommentToken = 10] = "InvalidCommentToken", e[e.UnexpectedEndOfComment = 11] = "UnexpectedEndOfComment", e[e.UnexpectedEndOfString = 12] = "UnexpectedEndOfString", e[e.UnexpectedEndOfNumber = 13] = "UnexpectedEndOfNumber", e[e.InvalidUnicode = 14] = "InvalidUnicode", e[e.InvalidEscapeCharacter = 15] = "InvalidEscapeCharacter", e[e.InvalidCharacter = 16] = "InvalidCharacter";
})(Qf || (Qf = {}));
var A1;
(() => {
  var e = { 975: (C) => {
    function A(T) {
      if (typeof T != "string") throw new TypeError("Path must be a string. Received " + JSON.stringify(T));
    }
    function _(T, P) {
      for (var V, Y = "", K = 0, J = -1, $ = 0, z = 0; z <= T.length; ++z) {
        if (z < T.length) V = T.charCodeAt(z);
        else {
          if (V === 47) break;
          V = 47;
        }
        if (V === 47) {
          if (!(J === z - 1 || $ === 1)) if (J !== z - 1 && $ === 2) {
            if (Y.length < 2 || K !== 2 || Y.charCodeAt(Y.length - 1) !== 46 || Y.charCodeAt(Y.length - 2) !== 46) {
              if (Y.length > 2) {
                var Z = Y.lastIndexOf("/");
                if (Z !== Y.length - 1) {
                  Z === -1 ? (Y = "", K = 0) : K = (Y = Y.slice(0, Z)).length - 1 - Y.lastIndexOf("/"), J = z, $ = 0;
                  continue;
                }
              } else if (Y.length === 2 || Y.length === 1) {
                Y = "", K = 0, J = z, $ = 0;
                continue;
              }
            }
            P && (Y.length > 0 ? Y += "/.." : Y = "..", K = 2);
          } else Y.length > 0 ? Y += "/" + T.slice(J + 1, z) : Y = T.slice(J + 1, z), K = z - J - 1;
          J = z, $ = 0;
        } else V === 46 && $ !== -1 ? ++$ : $ = -1;
      }
      return Y;
    }
    var O = { resolve: function() {
      for (var T, P = "", V = !1, Y = arguments.length - 1; Y >= -1 && !V; Y--) {
        var K;
        Y >= 0 ? K = arguments[Y] : (T === void 0 && (T = process.cwd()), K = T), A(K), K.length !== 0 && (P = K + "/" + P, V = K.charCodeAt(0) === 47);
      }
      return P = _(P, !V), V ? P.length > 0 ? "/" + P : "/" : P.length > 0 ? P : ".";
    }, normalize: function(T) {
      if (A(T), T.length === 0) return ".";
      var P = T.charCodeAt(0) === 47, V = T.charCodeAt(T.length - 1) === 47;
      return (T = _(T, !P)).length !== 0 || P || (T = "."), T.length > 0 && V && (T += "/"), P ? "/" + T : T;
    }, isAbsolute: function(T) {
      return A(T), T.length > 0 && T.charCodeAt(0) === 47;
    }, join: function() {
      if (arguments.length === 0) return ".";
      for (var T, P = 0; P < arguments.length; ++P) {
        var V = arguments[P];
        A(V), V.length > 0 && (T === void 0 ? T = V : T += "/" + V);
      }
      return T === void 0 ? "." : O.normalize(T);
    }, relative: function(T, P) {
      if (A(T), A(P), T === P || (T = O.resolve(T)) === (P = O.resolve(P))) return "";
      for (var V = 1; V < T.length && T.charCodeAt(V) === 47; ++V) ;
      for (var Y = T.length, K = Y - V, J = 1; J < P.length && P.charCodeAt(J) === 47; ++J) ;
      for (var $ = P.length - J, z = K < $ ? K : $, Z = -1, X = 0; X <= z; ++X) {
        if (X === z) {
          if ($ > z) {
            if (P.charCodeAt(J + X) === 47) return P.slice(J + X + 1);
            if (X === 0) return P.slice(J + X);
          } else K > z && (T.charCodeAt(V + X) === 47 ? Z = X : X === 0 && (Z = 0));
          break;
        }
        var ne = T.charCodeAt(V + X);
        if (ne !== P.charCodeAt(J + X)) break;
        ne === 47 && (Z = X);
      }
      var le = "";
      for (X = V + Z + 1; X <= Y; ++X) X !== Y && T.charCodeAt(X) !== 47 || (le.length === 0 ? le += ".." : le += "/..");
      return le.length > 0 ? le + P.slice(J + Z) : (J += Z, P.charCodeAt(J) === 47 && ++J, P.slice(J));
    }, _makeLong: function(T) {
      return T;
    }, dirname: function(T) {
      if (A(T), T.length === 0) return ".";
      for (var P = T.charCodeAt(0), V = P === 47, Y = -1, K = !0, J = T.length - 1; J >= 1; --J) if ((P = T.charCodeAt(J)) === 47) {
        if (!K) {
          Y = J;
          break;
        }
      } else K = !1;
      return Y === -1 ? V ? "/" : "." : V && Y === 1 ? "//" : T.slice(0, Y);
    }, basename: function(T, P) {
      if (P !== void 0 && typeof P != "string") throw new TypeError('"ext" argument must be a string');
      A(T);
      var V, Y = 0, K = -1, J = !0;
      if (P !== void 0 && P.length > 0 && P.length <= T.length) {
        if (P.length === T.length && P === T) return "";
        var $ = P.length - 1, z = -1;
        for (V = T.length - 1; V >= 0; --V) {
          var Z = T.charCodeAt(V);
          if (Z === 47) {
            if (!J) {
              Y = V + 1;
              break;
            }
          } else z === -1 && (J = !1, z = V + 1), $ >= 0 && (Z === P.charCodeAt($) ? --$ == -1 && (K = V) : ($ = -1, K = z));
        }
        return Y === K ? K = z : K === -1 && (K = T.length), T.slice(Y, K);
      }
      for (V = T.length - 1; V >= 0; --V) if (T.charCodeAt(V) === 47) {
        if (!J) {
          Y = V + 1;
          break;
        }
      } else K === -1 && (J = !1, K = V + 1);
      return K === -1 ? "" : T.slice(Y, K);
    }, extname: function(T) {
      A(T);
      for (var P = -1, V = 0, Y = -1, K = !0, J = 0, $ = T.length - 1; $ >= 0; --$) {
        var z = T.charCodeAt($);
        if (z !== 47) Y === -1 && (K = !1, Y = $ + 1), z === 46 ? P === -1 ? P = $ : J !== 1 && (J = 1) : P !== -1 && (J = -1);
        else if (!K) {
          V = $ + 1;
          break;
        }
      }
      return P === -1 || Y === -1 || J === 0 || J === 1 && P === Y - 1 && P === V + 1 ? "" : T.slice(P, Y);
    }, format: function(T) {
      if (T === null || typeof T != "object") throw new TypeError('The "pathObject" argument must be of type Object. Received type ' + typeof T);
      return (function(P, V) {
        var Y = V.dir || V.root, K = V.base || (V.name || "") + (V.ext || "");
        return Y ? Y === V.root ? Y + K : Y + "/" + K : K;
      })(0, T);
    }, parse: function(T) {
      A(T);
      var P = { root: "", dir: "", base: "", ext: "", name: "" };
      if (T.length === 0) return P;
      var V, Y = T.charCodeAt(0), K = Y === 47;
      K ? (P.root = "/", V = 1) : V = 0;
      for (var J = -1, $ = 0, z = -1, Z = !0, X = T.length - 1, ne = 0; X >= V; --X) if ((Y = T.charCodeAt(X)) !== 47) z === -1 && (Z = !1, z = X + 1), Y === 46 ? J === -1 ? J = X : ne !== 1 && (ne = 1) : J !== -1 && (ne = -1);
      else if (!Z) {
        $ = X + 1;
        break;
      }
      return J === -1 || z === -1 || ne === 0 || ne === 1 && J === z - 1 && J === $ + 1 ? z !== -1 && (P.base = P.name = $ === 0 && K ? T.slice(1, z) : T.slice($, z)) : ($ === 0 && K ? (P.name = T.slice(1, J), P.base = T.slice(1, z)) : (P.name = T.slice($, J), P.base = T.slice($, z)), P.ext = T.slice(J, z)), $ > 0 ? P.dir = T.slice(0, $ - 1) : K && (P.dir = "/"), P;
    }, sep: "/", delimiter: ":", win32: null, posix: null };
    O.posix = O, C.exports = O;
  } }, t = {};
  function n(C) {
    var A = t[C];
    if (A !== void 0) return A.exports;
    var _ = t[C] = { exports: {} };
    return e[C](_, _.exports, n), _.exports;
  }
  n.d = (C, A) => {
    for (var _ in A) n.o(A, _) && !n.o(C, _) && Object.defineProperty(C, _, { enumerable: !0, get: A[_] });
  }, n.o = (C, A) => Object.prototype.hasOwnProperty.call(C, A), n.r = (C) => {
    typeof Symbol < "u" && Symbol.toStringTag && Object.defineProperty(C, Symbol.toStringTag, { value: "Module" }), Object.defineProperty(C, "__esModule", { value: !0 });
  };
  var r = {};
  let s;
  n.r(r), n.d(r, { URI: () => d, Utils: () => L }), typeof process == "object" ? s = process.platform === "win32" : typeof navigator == "object" && (s = navigator.userAgent.indexOf("Windows") >= 0);
  const i = /^\w[\w\d+.-]*$/, a = /^\//, o = /^\/\//;
  function l(C, A) {
    if (!C.scheme && A) throw new Error(`[UriError]: Scheme is missing: {scheme: "", authority: "${C.authority}", path: "${C.path}", query: "${C.query}", fragment: "${C.fragment}"}`);
    if (C.scheme && !i.test(C.scheme)) throw new Error("[UriError]: Scheme contains illegal characters.");
    if (C.path) {
      if (C.authority) {
        if (!a.test(C.path)) throw new Error('[UriError]: If a URI contains an authority component, then the path component must either be empty or begin with a slash ("/") character');
      } else if (o.test(C.path)) throw new Error('[UriError]: If a URI does not contain an authority component, then the path cannot begin with two slash characters ("//")');
    }
  }
  const u = "", f = "/", c = /^(([^:/?#]+?):)?(\/\/([^/?#]*))?([^?#]*)(\?([^#]*))?(#(.*))?/;
  class d {
    static isUri(A) {
      return A instanceof d || !!A && typeof A.authority == "string" && typeof A.fragment == "string" && typeof A.path == "string" && typeof A.query == "string" && typeof A.scheme == "string" && typeof A.fsPath == "string" && typeof A.with == "function" && typeof A.toString == "function";
    }
    scheme;
    authority;
    path;
    query;
    fragment;
    constructor(A, _, O, T, P, V = !1) {
      typeof A == "object" ? (this.scheme = A.scheme || u, this.authority = A.authority || u, this.path = A.path || u, this.query = A.query || u, this.fragment = A.fragment || u) : (this.scheme = /* @__PURE__ */ (function(Y, K) {
        return Y || K ? Y : "file";
      })(A, V), this.authority = _ || u, this.path = (function(Y, K) {
        switch (Y) {
          case "https":
          case "http":
          case "file":
            K ? K[0] !== f && (K = f + K) : K = f;
        }
        return K;
      })(this.scheme, O || u), this.query = T || u, this.fragment = P || u, l(this, V));
    }
    get fsPath() {
      return k(this);
    }
    with(A) {
      if (!A) return this;
      let { scheme: _, authority: O, path: T, query: P, fragment: V } = A;
      return _ === void 0 ? _ = this.scheme : _ === null && (_ = u), O === void 0 ? O = this.authority : O === null && (O = u), T === void 0 ? T = this.path : T === null && (T = u), P === void 0 ? P = this.query : P === null && (P = u), V === void 0 ? V = this.fragment : V === null && (V = u), _ === this.scheme && O === this.authority && T === this.path && P === this.query && V === this.fragment ? this : new D(_, O, T, P, V);
    }
    static parse(A, _ = !1) {
      const O = c.exec(A);
      return O ? new D(O[2] || u, m(O[4] || u), m(O[5] || u), m(O[7] || u), m(O[9] || u), _) : new D(u, u, u, u, u);
    }
    static file(A) {
      let _ = u;
      if (s && (A = A.replace(/\\/g, f)), A[0] === f && A[1] === f) {
        const O = A.indexOf(f, 2);
        O === -1 ? (_ = A.substring(2), A = f) : (_ = A.substring(2, O), A = A.substring(O) || f);
      }
      return new D("file", _, A, u, u);
    }
    static from(A) {
      const _ = new D(A.scheme, A.authority, A.path, A.query, A.fragment);
      return l(_, !0), _;
    }
    toString(A = !1) {
      return y(this, A);
    }
    toJSON() {
      return this;
    }
    static revive(A) {
      if (A) {
        if (A instanceof d) return A;
        {
          const _ = new D(A);
          return _._formatted = A.external, _._fsPath = A._sep === v ? A.fsPath : null, _;
        }
      }
      return A;
    }
  }
  const v = s ? 1 : void 0;
  class D extends d {
    _formatted = null;
    _fsPath = null;
    get fsPath() {
      return this._fsPath || (this._fsPath = k(this)), this._fsPath;
    }
    toString(A = !1) {
      return A ? y(this, !0) : (this._formatted || (this._formatted = y(this, !1)), this._formatted);
    }
    toJSON() {
      const A = { $mid: 1 };
      return this._fsPath && (A.fsPath = this._fsPath, A._sep = v), this._formatted && (A.external = this._formatted), this.path && (A.path = this.path), this.scheme && (A.scheme = this.scheme), this.authority && (A.authority = this.authority), this.query && (A.query = this.query), this.fragment && (A.fragment = this.fragment), A;
    }
  }
  const S = { 58: "%3A", 47: "%2F", 63: "%3F", 35: "%23", 91: "%5B", 93: "%5D", 64: "%40", 33: "%21", 36: "%24", 38: "%26", 39: "%27", 40: "%28", 41: "%29", 42: "%2A", 43: "%2B", 44: "%2C", 59: "%3B", 61: "%3D", 32: "%20" };
  function x(C, A, _) {
    let O, T = -1;
    for (let P = 0; P < C.length; P++) {
      const V = C.charCodeAt(P);
      if (V >= 97 && V <= 122 || V >= 65 && V <= 90 || V >= 48 && V <= 57 || V === 45 || V === 46 || V === 95 || V === 126 || A && V === 47 || _ && V === 91 || _ && V === 93 || _ && V === 58) T !== -1 && (O += encodeURIComponent(C.substring(T, P)), T = -1), O !== void 0 && (O += C.charAt(P));
      else {
        O === void 0 && (O = C.substr(0, P));
        const Y = S[V];
        Y !== void 0 ? (T !== -1 && (O += encodeURIComponent(C.substring(T, P)), T = -1), O += Y) : T === -1 && (T = P);
      }
    }
    return T !== -1 && (O += encodeURIComponent(C.substring(T))), O !== void 0 ? O : C;
  }
  function N(C) {
    let A;
    for (let _ = 0; _ < C.length; _++) {
      const O = C.charCodeAt(_);
      O === 35 || O === 63 ? (A === void 0 && (A = C.substr(0, _)), A += S[O]) : A !== void 0 && (A += C[_]);
    }
    return A !== void 0 ? A : C;
  }
  function k(C, A) {
    let _;
    return _ = C.authority && C.path.length > 1 && C.scheme === "file" ? `//${C.authority}${C.path}` : C.path.charCodeAt(0) === 47 && (C.path.charCodeAt(1) >= 65 && C.path.charCodeAt(1) <= 90 || C.path.charCodeAt(1) >= 97 && C.path.charCodeAt(1) <= 122) && C.path.charCodeAt(2) === 58 ? C.path[1].toLowerCase() + C.path.substr(2) : C.path, s && (_ = _.replace(/\//g, "\\")), _;
  }
  function y(C, A) {
    const _ = A ? N : x;
    let O = "", { scheme: T, authority: P, path: V, query: Y, fragment: K } = C;
    if (T && (O += T, O += ":"), (P || T === "file") && (O += f, O += f), P) {
      let J = P.indexOf("@");
      if (J !== -1) {
        const $ = P.substr(0, J);
        P = P.substr(J + 1), J = $.lastIndexOf(":"), J === -1 ? O += _($, !1, !1) : (O += _($.substr(0, J), !1, !1), O += ":", O += _($.substr(J + 1), !1, !0)), O += "@";
      }
      P = P.toLowerCase(), J = P.lastIndexOf(":"), J === -1 ? O += _(P, !1, !0) : (O += _(P.substr(0, J), !1, !0), O += P.substr(J));
    }
    if (V) {
      if (V.length >= 3 && V.charCodeAt(0) === 47 && V.charCodeAt(2) === 58) {
        const J = V.charCodeAt(1);
        J >= 65 && J <= 90 && (V = `/${String.fromCharCode(J + 32)}:${V.substr(3)}`);
      } else if (V.length >= 2 && V.charCodeAt(1) === 58) {
        const J = V.charCodeAt(0);
        J >= 65 && J <= 90 && (V = `${String.fromCharCode(J + 32)}:${V.substr(2)}`);
      }
      O += _(V, !0, !1);
    }
    return Y && (O += "?", O += _(Y, !1, !1)), K && (O += "#", O += A ? K : x(K, !1, !1)), O;
  }
  function b(C) {
    try {
      return decodeURIComponent(C);
    } catch {
      return C.length > 3 ? C.substr(0, 3) + b(C.substr(3)) : C;
    }
  }
  const h = /(%[0-9A-Za-z][0-9A-Za-z])+/g;
  function m(C) {
    return C.match(h) ? C.replace(h, ((A) => b(A))) : C;
  }
  var p = n(975);
  const E = p.posix || p, w = "/";
  var L;
  (function(C) {
    C.joinPath = function(A, ..._) {
      return A.with({ path: E.join(A.path, ..._) });
    }, C.resolvePath = function(A, ..._) {
      let O = A.path, T = !1;
      O[0] !== w && (O = w + O, T = !0);
      let P = E.resolve(O, ..._);
      return T && P[0] === w && !A.authority && (P = P.substring(1)), A.with({ path: P });
    }, C.dirname = function(A) {
      if (A.path.length === 0 || A.path === w) return A;
      let _ = E.dirname(A.path);
      return _.length === 1 && _.charCodeAt(0) === 46 && (_ = ""), A.with({ path: _ });
    }, C.basename = function(A) {
      return E.basename(A.path);
    }, C.extname = function(A) {
      return E.extname(A.path);
    };
  })(L || (L = {})), A1 = r;
})();
const { URI: yt, Utils: _6 } = A1;
var Kf;
(function(e) {
  function t(n) {
    return typeof n == "string";
  }
  e.is = t;
})(Kf || (Kf = {}));
var nl;
(function(e) {
  function t(n) {
    return typeof n == "string";
  }
  e.is = t;
})(nl || (nl = {}));
var Xf;
(function(e) {
  e.MIN_VALUE = -2147483648, e.MAX_VALUE = 2147483647;
  function t(n) {
    return typeof n == "number" && e.MIN_VALUE <= n && n <= e.MAX_VALUE;
  }
  e.is = t;
})(Xf || (Xf = {}));
var na;
(function(e) {
  e.MIN_VALUE = 0, e.MAX_VALUE = 2147483647;
  function t(n) {
    return typeof n == "number" && e.MIN_VALUE <= n && n <= e.MAX_VALUE;
  }
  e.is = t;
})(na || (na = {}));
var Ye;
(function(e) {
  function t(r, s) {
    return r === Number.MAX_VALUE && (r = na.MAX_VALUE), s === Number.MAX_VALUE && (s = na.MAX_VALUE), { line: r, character: s };
  }
  e.create = t;
  function n(r) {
    let s = r;
    return q.objectLiteral(s) && q.uinteger(s.line) && q.uinteger(s.character);
  }
  e.is = n;
})(Ye || (Ye = {}));
var ie;
(function(e) {
  function t(r, s, i, a) {
    if (q.uinteger(r) && q.uinteger(s) && q.uinteger(i) && q.uinteger(a))
      return { start: Ye.create(r, s), end: Ye.create(i, a) };
    if (Ye.is(r) && Ye.is(s))
      return { start: r, end: s };
    throw new Error(`Range#create called with invalid arguments[${r}, ${s}, ${i}, ${a}]`);
  }
  e.create = t;
  function n(r) {
    let s = r;
    return q.objectLiteral(s) && Ye.is(s.start) && Ye.is(s.end);
  }
  e.is = n;
})(ie || (ie = {}));
var ts;
(function(e) {
  function t(r, s) {
    return { uri: r, range: s };
  }
  e.create = t;
  function n(r) {
    let s = r;
    return q.objectLiteral(s) && ie.is(s.range) && (q.string(s.uri) || q.undefined(s.uri));
  }
  e.is = n;
})(ts || (ts = {}));
var rl;
(function(e) {
  function t(r, s, i, a) {
    return { targetUri: r, targetRange: s, targetSelectionRange: i, originSelectionRange: a };
  }
  e.create = t;
  function n(r) {
    let s = r;
    return q.objectLiteral(s) && ie.is(s.targetRange) && q.string(s.targetUri) && ie.is(s.targetSelectionRange) && (ie.is(s.originSelectionRange) || q.undefined(s.originSelectionRange));
  }
  e.is = n;
})(rl || (rl = {}));
var sl;
(function(e) {
  function t(r, s, i, a) {
    return {
      red: r,
      green: s,
      blue: i,
      alpha: a
    };
  }
  e.create = t;
  function n(r) {
    const s = r;
    return q.objectLiteral(s) && q.numberRange(s.red, 0, 1) && q.numberRange(s.green, 0, 1) && q.numberRange(s.blue, 0, 1) && q.numberRange(s.alpha, 0, 1);
  }
  e.is = n;
})(sl || (sl = {}));
var Zf;
(function(e) {
  function t(r, s) {
    return {
      range: r,
      color: s
    };
  }
  e.create = t;
  function n(r) {
    const s = r;
    return q.objectLiteral(s) && ie.is(s.range) && sl.is(s.color);
  }
  e.is = n;
})(Zf || (Zf = {}));
var eh;
(function(e) {
  function t(r, s, i) {
    return {
      label: r,
      textEdit: s,
      additionalTextEdits: i
    };
  }
  e.create = t;
  function n(r) {
    const s = r;
    return q.objectLiteral(s) && q.string(s.label) && (q.undefined(s.textEdit) || _e.is(s)) && (q.undefined(s.additionalTextEdits) || q.typedArray(s.additionalTextEdits, _e.is));
  }
  e.is = n;
})(eh || (eh = {}));
var th;
(function(e) {
  e.Comment = "comment", e.Imports = "imports", e.Region = "region";
})(th || (th = {}));
var il;
(function(e) {
  function t(r, s, i, a, o, l) {
    const u = {
      startLine: r,
      endLine: s
    };
    return q.defined(i) && (u.startCharacter = i), q.defined(a) && (u.endCharacter = a), q.defined(o) && (u.kind = o), q.defined(l) && (u.collapsedText = l), u;
  }
  e.create = t;
  function n(r) {
    const s = r;
    return q.objectLiteral(s) && q.uinteger(s.startLine) && q.uinteger(s.startLine) && (q.undefined(s.startCharacter) || q.uinteger(s.startCharacter)) && (q.undefined(s.endCharacter) || q.uinteger(s.endCharacter)) && (q.undefined(s.kind) || q.string(s.kind));
  }
  e.is = n;
})(il || (il = {}));
var al;
(function(e) {
  function t(r, s) {
    return {
      location: r,
      message: s
    };
  }
  e.create = t;
  function n(r) {
    let s = r;
    return q.defined(s) && ts.is(s.location) && q.string(s.message);
  }
  e.is = n;
})(al || (al = {}));
var ce;
(function(e) {
  e.Error = 1, e.Warning = 2, e.Information = 3, e.Hint = 4;
})(ce || (ce = {}));
var ol;
(function(e) {
  e.Unnecessary = 1, e.Deprecated = 2;
})(ol || (ol = {}));
var nh;
(function(e) {
  function t(n) {
    const r = n;
    return q.objectLiteral(r) && q.string(r.href);
  }
  e.is = t;
})(nh || (nh = {}));
var bt;
(function(e) {
  function t(r, s, i, a, o, l) {
    let u = { range: r, message: s };
    return q.defined(i) && (u.severity = i), q.defined(a) && (u.code = a), q.defined(o) && (u.source = o), q.defined(l) && (u.relatedInformation = l), u;
  }
  e.create = t;
  function n(r) {
    var s;
    let i = r;
    return q.defined(i) && ie.is(i.range) && q.string(i.message) && (q.number(i.severity) || q.undefined(i.severity)) && (q.integer(i.code) || q.string(i.code) || q.undefined(i.code)) && (q.undefined(i.codeDescription) || q.string((s = i.codeDescription) === null || s === void 0 ? void 0 : s.href)) && (q.string(i.source) || q.undefined(i.source)) && (q.undefined(i.relatedInformation) || q.typedArray(i.relatedInformation, al.is));
  }
  e.is = n;
})(bt || (bt = {}));
var ir;
(function(e) {
  function t(r, s, ...i) {
    let a = { title: r, command: s };
    return q.defined(i) && i.length > 0 && (a.arguments = i), a;
  }
  e.create = t;
  function n(r) {
    let s = r;
    return q.defined(s) && q.string(s.title) && q.string(s.command);
  }
  e.is = n;
})(ir || (ir = {}));
var _e;
(function(e) {
  function t(i, a) {
    return { range: i, newText: a };
  }
  e.replace = t;
  function n(i, a) {
    return { range: { start: i, end: i }, newText: a };
  }
  e.insert = n;
  function r(i) {
    return { range: i, newText: "" };
  }
  e.del = r;
  function s(i) {
    const a = i;
    return q.objectLiteral(a) && q.string(a.newText) && ie.is(a.range);
  }
  e.is = s;
})(_e || (_e = {}));
var ll;
(function(e) {
  function t(r, s, i) {
    const a = { label: r };
    return s !== void 0 && (a.needsConfirmation = s), i !== void 0 && (a.description = i), a;
  }
  e.create = t;
  function n(r) {
    const s = r;
    return q.objectLiteral(s) && q.string(s.label) && (q.boolean(s.needsConfirmation) || s.needsConfirmation === void 0) && (q.string(s.description) || s.description === void 0);
  }
  e.is = n;
})(ll || (ll = {}));
var ns;
(function(e) {
  function t(n) {
    const r = n;
    return q.string(r);
  }
  e.is = t;
})(ns || (ns = {}));
var rh;
(function(e) {
  function t(i, a, o) {
    return { range: i, newText: a, annotationId: o };
  }
  e.replace = t;
  function n(i, a, o) {
    return { range: { start: i, end: i }, newText: a, annotationId: o };
  }
  e.insert = n;
  function r(i, a) {
    return { range: i, newText: "", annotationId: a };
  }
  e.del = r;
  function s(i) {
    const a = i;
    return _e.is(a) && (ll.is(a.annotationId) || ns.is(a.annotationId));
  }
  e.is = s;
})(rh || (rh = {}));
var ul;
(function(e) {
  function t(r, s) {
    return { textDocument: r, edits: s };
  }
  e.create = t;
  function n(r) {
    let s = r;
    return q.defined(s) && ml.is(s.textDocument) && Array.isArray(s.edits);
  }
  e.is = n;
})(ul || (ul = {}));
var cl;
(function(e) {
  function t(r, s, i) {
    let a = {
      kind: "create",
      uri: r
    };
    return s !== void 0 && (s.overwrite !== void 0 || s.ignoreIfExists !== void 0) && (a.options = s), i !== void 0 && (a.annotationId = i), a;
  }
  e.create = t;
  function n(r) {
    let s = r;
    return s && s.kind === "create" && q.string(s.uri) && (s.options === void 0 || (s.options.overwrite === void 0 || q.boolean(s.options.overwrite)) && (s.options.ignoreIfExists === void 0 || q.boolean(s.options.ignoreIfExists))) && (s.annotationId === void 0 || ns.is(s.annotationId));
  }
  e.is = n;
})(cl || (cl = {}));
var fl;
(function(e) {
  function t(r, s, i, a) {
    let o = {
      kind: "rename",
      oldUri: r,
      newUri: s
    };
    return i !== void 0 && (i.overwrite !== void 0 || i.ignoreIfExists !== void 0) && (o.options = i), a !== void 0 && (o.annotationId = a), o;
  }
  e.create = t;
  function n(r) {
    let s = r;
    return s && s.kind === "rename" && q.string(s.oldUri) && q.string(s.newUri) && (s.options === void 0 || (s.options.overwrite === void 0 || q.boolean(s.options.overwrite)) && (s.options.ignoreIfExists === void 0 || q.boolean(s.options.ignoreIfExists))) && (s.annotationId === void 0 || ns.is(s.annotationId));
  }
  e.is = n;
})(fl || (fl = {}));
var hl;
(function(e) {
  function t(r, s, i) {
    let a = {
      kind: "delete",
      uri: r
    };
    return s !== void 0 && (s.recursive !== void 0 || s.ignoreIfNotExists !== void 0) && (a.options = s), i !== void 0 && (a.annotationId = i), a;
  }
  e.create = t;
  function n(r) {
    let s = r;
    return s && s.kind === "delete" && q.string(s.uri) && (s.options === void 0 || (s.options.recursive === void 0 || q.boolean(s.options.recursive)) && (s.options.ignoreIfNotExists === void 0 || q.boolean(s.options.ignoreIfNotExists))) && (s.annotationId === void 0 || ns.is(s.annotationId));
  }
  e.is = n;
})(hl || (hl = {}));
var dl;
(function(e) {
  function t(n) {
    let r = n;
    return r && (r.changes !== void 0 || r.documentChanges !== void 0) && (r.documentChanges === void 0 || r.documentChanges.every((s) => q.string(s.kind) ? cl.is(s) || fl.is(s) || hl.is(s) : ul.is(s)));
  }
  e.is = t;
})(dl || (dl = {}));
var sh;
(function(e) {
  function t(r) {
    return { uri: r };
  }
  e.create = t;
  function n(r) {
    let s = r;
    return q.defined(s) && q.string(s.uri);
  }
  e.is = n;
})(sh || (sh = {}));
var ih;
(function(e) {
  function t(r, s) {
    return { uri: r, version: s };
  }
  e.create = t;
  function n(r) {
    let s = r;
    return q.defined(s) && q.string(s.uri) && q.integer(s.version);
  }
  e.is = n;
})(ih || (ih = {}));
var ml;
(function(e) {
  function t(r, s) {
    return { uri: r, version: s };
  }
  e.create = t;
  function n(r) {
    let s = r;
    return q.defined(s) && q.string(s.uri) && (s.version === null || q.integer(s.version));
  }
  e.is = n;
})(ml || (ml = {}));
var ah;
(function(e) {
  function t(r, s, i, a) {
    return { uri: r, languageId: s, version: i, text: a };
  }
  e.create = t;
  function n(r) {
    let s = r;
    return q.defined(s) && q.string(s.uri) && q.string(s.languageId) && q.integer(s.version) && q.string(s.text);
  }
  e.is = n;
})(ah || (ah = {}));
var hn;
(function(e) {
  e.PlainText = "plaintext", e.Markdown = "markdown";
  function t(n) {
    const r = n;
    return r === e.PlainText || r === e.Markdown;
  }
  e.is = t;
})(hn || (hn = {}));
var Qs;
(function(e) {
  function t(n) {
    const r = n;
    return q.objectLiteral(n) && hn.is(r.kind) && q.string(r.value);
  }
  e.is = t;
})(Qs || (Qs = {}));
var pt;
(function(e) {
  e.Text = 1, e.Method = 2, e.Function = 3, e.Constructor = 4, e.Field = 5, e.Variable = 6, e.Class = 7, e.Interface = 8, e.Module = 9, e.Property = 10, e.Unit = 11, e.Value = 12, e.Enum = 13, e.Keyword = 14, e.Snippet = 15, e.Color = 16, e.File = 17, e.Reference = 18, e.Folder = 19, e.EnumMember = 20, e.Constant = 21, e.Struct = 22, e.Event = 23, e.Operator = 24, e.TypeParameter = 25;
})(pt || (pt = {}));
var ze;
(function(e) {
  e.PlainText = 1, e.Snippet = 2;
})(ze || (ze = {}));
var oh;
(function(e) {
  e.Deprecated = 1;
})(oh || (oh = {}));
var lh;
(function(e) {
  function t(r, s, i) {
    return { newText: r, insert: s, replace: i };
  }
  e.create = t;
  function n(r) {
    const s = r;
    return s && q.string(s.newText) && ie.is(s.insert) && ie.is(s.replace);
  }
  e.is = n;
})(lh || (lh = {}));
var pl;
(function(e) {
  e.asIs = 1, e.adjustIndentation = 2;
})(pl || (pl = {}));
var uh;
(function(e) {
  function t(n) {
    const r = n;
    return r && (q.string(r.detail) || r.detail === void 0) && (q.string(r.description) || r.description === void 0);
  }
  e.is = t;
})(uh || (uh = {}));
var gl;
(function(e) {
  function t(n) {
    return { label: n };
  }
  e.create = t;
})(gl || (gl = {}));
var yl;
(function(e) {
  function t(n, r) {
    return { items: n || [], isIncomplete: !!r };
  }
  e.create = t;
})(yl || (yl = {}));
var ra;
(function(e) {
  function t(r) {
    return r.replace(/[\\`*_{}[\]()#+\-.!]/g, "\\$&");
  }
  e.fromPlainText = t;
  function n(r) {
    const s = r;
    return q.string(s) || q.objectLiteral(s) && q.string(s.language) && q.string(s.value);
  }
  e.is = n;
})(ra || (ra = {}));
var ch;
(function(e) {
  function t(n) {
    let r = n;
    return !!r && q.objectLiteral(r) && (Qs.is(r.contents) || ra.is(r.contents) || q.typedArray(r.contents, ra.is)) && (n.range === void 0 || ie.is(n.range));
  }
  e.is = t;
})(ch || (ch = {}));
var fh;
(function(e) {
  function t(n, r) {
    return r ? { label: n, documentation: r } : { label: n };
  }
  e.create = t;
})(fh || (fh = {}));
var hh;
(function(e) {
  function t(n, r, ...s) {
    let i = { label: n };
    return q.defined(r) && (i.documentation = r), q.defined(s) ? i.parameters = s : i.parameters = [], i;
  }
  e.create = t;
})(hh || (hh = {}));
var dh;
(function(e) {
  e.Text = 1, e.Read = 2, e.Write = 3;
})(dh || (dh = {}));
var mh;
(function(e) {
  function t(n, r) {
    let s = { range: n };
    return q.number(r) && (s.kind = r), s;
  }
  e.create = t;
})(mh || (mh = {}));
var Ut;
(function(e) {
  e.File = 1, e.Module = 2, e.Namespace = 3, e.Package = 4, e.Class = 5, e.Method = 6, e.Property = 7, e.Field = 8, e.Constructor = 9, e.Enum = 10, e.Interface = 11, e.Function = 12, e.Variable = 13, e.Constant = 14, e.String = 15, e.Number = 16, e.Boolean = 17, e.Array = 18, e.Object = 19, e.Key = 20, e.Null = 21, e.EnumMember = 22, e.Struct = 23, e.Event = 24, e.Operator = 25, e.TypeParameter = 26;
})(Ut || (Ut = {}));
var ph;
(function(e) {
  e.Deprecated = 1;
})(ph || (ph = {}));
var gh;
(function(e) {
  function t(n, r, s, i, a) {
    let o = {
      name: n,
      kind: r,
      location: { uri: i, range: s }
    };
    return a && (o.containerName = a), o;
  }
  e.create = t;
})(gh || (gh = {}));
var yh;
(function(e) {
  function t(n, r, s, i) {
    return i !== void 0 ? { name: n, kind: r, location: { uri: s, range: i } } : { name: n, kind: r, location: { uri: s } };
  }
  e.create = t;
})(yh || (yh = {}));
var bh;
(function(e) {
  function t(r, s, i, a, o, l) {
    let u = {
      name: r,
      detail: s,
      kind: i,
      range: a,
      selectionRange: o
    };
    return l !== void 0 && (u.children = l), u;
  }
  e.create = t;
  function n(r) {
    let s = r;
    return s && q.string(s.name) && q.number(s.kind) && ie.is(s.range) && ie.is(s.selectionRange) && (s.detail === void 0 || q.string(s.detail)) && (s.deprecated === void 0 || q.boolean(s.deprecated)) && (s.children === void 0 || Array.isArray(s.children)) && (s.tags === void 0 || Array.isArray(s.tags));
  }
  e.is = n;
})(bh || (bh = {}));
var on;
(function(e) {
  e.Empty = "", e.QuickFix = "quickfix", e.Refactor = "refactor", e.RefactorExtract = "refactor.extract", e.RefactorInline = "refactor.inline", e.RefactorRewrite = "refactor.rewrite", e.Source = "source", e.SourceOrganizeImports = "source.organizeImports", e.SourceFixAll = "source.fixAll";
})(on || (on = {}));
var sa;
(function(e) {
  e.Invoked = 1, e.Automatic = 2;
})(sa || (sa = {}));
var vh;
(function(e) {
  function t(r, s, i) {
    let a = { diagnostics: r };
    return s != null && (a.only = s), i != null && (a.triggerKind = i), a;
  }
  e.create = t;
  function n(r) {
    let s = r;
    return q.defined(s) && q.typedArray(s.diagnostics, bt.is) && (s.only === void 0 || q.typedArray(s.only, q.string)) && (s.triggerKind === void 0 || s.triggerKind === sa.Invoked || s.triggerKind === sa.Automatic);
  }
  e.is = n;
})(vh || (vh = {}));
var qt;
(function(e) {
  function t(r, s, i) {
    let a = { title: r }, o = !0;
    return typeof s == "string" ? (o = !1, a.kind = s) : ir.is(s) ? a.command = s : a.edit = s, o && i !== void 0 && (a.kind = i), a;
  }
  e.create = t;
  function n(r) {
    let s = r;
    return s && q.string(s.title) && (s.diagnostics === void 0 || q.typedArray(s.diagnostics, bt.is)) && (s.kind === void 0 || q.string(s.kind)) && (s.edit !== void 0 || s.command !== void 0) && (s.command === void 0 || ir.is(s.command)) && (s.isPreferred === void 0 || q.boolean(s.isPreferred)) && (s.edit === void 0 || dl.is(s.edit));
  }
  e.is = n;
})(qt || (qt = {}));
var bl;
(function(e) {
  function t(r, s) {
    let i = { range: r };
    return q.defined(s) && (i.data = s), i;
  }
  e.create = t;
  function n(r) {
    let s = r;
    return q.defined(s) && ie.is(s.range) && (q.undefined(s.command) || ir.is(s.command));
  }
  e.is = n;
})(bl || (bl = {}));
var wh;
(function(e) {
  function t(r, s) {
    return { tabSize: r, insertSpaces: s };
  }
  e.create = t;
  function n(r) {
    let s = r;
    return q.defined(s) && q.uinteger(s.tabSize) && q.boolean(s.insertSpaces);
  }
  e.is = n;
})(wh || (wh = {}));
var Dh;
(function(e) {
  function t(r, s, i) {
    return { range: r, target: s, data: i };
  }
  e.create = t;
  function n(r) {
    let s = r;
    return q.defined(s) && ie.is(s.range) && (q.undefined(s.target) || q.string(s.target));
  }
  e.is = n;
})(Dh || (Dh = {}));
var ia;
(function(e) {
  function t(r, s) {
    return { range: r, parent: s };
  }
  e.create = t;
  function n(r) {
    let s = r;
    return q.objectLiteral(s) && ie.is(s.range) && (s.parent === void 0 || e.is(s.parent));
  }
  e.is = n;
})(ia || (ia = {}));
var Sh;
(function(e) {
  e.namespace = "namespace", e.type = "type", e.class = "class", e.enum = "enum", e.interface = "interface", e.struct = "struct", e.typeParameter = "typeParameter", e.parameter = "parameter", e.variable = "variable", e.property = "property", e.enumMember = "enumMember", e.event = "event", e.function = "function", e.method = "method", e.macro = "macro", e.keyword = "keyword", e.modifier = "modifier", e.comment = "comment", e.string = "string", e.number = "number", e.regexp = "regexp", e.operator = "operator", e.decorator = "decorator";
})(Sh || (Sh = {}));
var Eh;
(function(e) {
  e.declaration = "declaration", e.definition = "definition", e.readonly = "readonly", e.static = "static", e.deprecated = "deprecated", e.abstract = "abstract", e.async = "async", e.modification = "modification", e.documentation = "documentation", e.defaultLibrary = "defaultLibrary";
})(Eh || (Eh = {}));
var Ah;
(function(e) {
  function t(n) {
    const r = n;
    return q.objectLiteral(r) && (r.resultId === void 0 || typeof r.resultId == "string") && Array.isArray(r.data) && (r.data.length === 0 || typeof r.data[0] == "number");
  }
  e.is = t;
})(Ah || (Ah = {}));
var xh;
(function(e) {
  function t(r, s) {
    return { range: r, text: s };
  }
  e.create = t;
  function n(r) {
    const s = r;
    return s != null && ie.is(s.range) && q.string(s.text);
  }
  e.is = n;
})(xh || (xh = {}));
var Nh;
(function(e) {
  function t(r, s, i) {
    return { range: r, variableName: s, caseSensitiveLookup: i };
  }
  e.create = t;
  function n(r) {
    const s = r;
    return s != null && ie.is(s.range) && q.boolean(s.caseSensitiveLookup) && (q.string(s.variableName) || s.variableName === void 0);
  }
  e.is = n;
})(Nh || (Nh = {}));
var Lh;
(function(e) {
  function t(r, s) {
    return { range: r, expression: s };
  }
  e.create = t;
  function n(r) {
    const s = r;
    return s != null && ie.is(s.range) && (q.string(s.expression) || s.expression === void 0);
  }
  e.is = n;
})(Lh || (Lh = {}));
var kh;
(function(e) {
  function t(r, s) {
    return { frameId: r, stoppedLocation: s };
  }
  e.create = t;
  function n(r) {
    const s = r;
    return q.defined(s) && ie.is(r.stoppedLocation);
  }
  e.is = n;
})(kh || (kh = {}));
var vl;
(function(e) {
  e.Type = 1, e.Parameter = 2;
  function t(n) {
    return n === 1 || n === 2;
  }
  e.is = t;
})(vl || (vl = {}));
var wl;
(function(e) {
  function t(r) {
    return { value: r };
  }
  e.create = t;
  function n(r) {
    const s = r;
    return q.objectLiteral(s) && (s.tooltip === void 0 || q.string(s.tooltip) || Qs.is(s.tooltip)) && (s.location === void 0 || ts.is(s.location)) && (s.command === void 0 || ir.is(s.command));
  }
  e.is = n;
})(wl || (wl = {}));
var Ch;
(function(e) {
  function t(r, s, i) {
    const a = { position: r, label: s };
    return i !== void 0 && (a.kind = i), a;
  }
  e.create = t;
  function n(r) {
    const s = r;
    return q.objectLiteral(s) && Ye.is(s.position) && (q.string(s.label) || q.typedArray(s.label, wl.is)) && (s.kind === void 0 || vl.is(s.kind)) && s.textEdits === void 0 || q.typedArray(s.textEdits, _e.is) && (s.tooltip === void 0 || q.string(s.tooltip) || Qs.is(s.tooltip)) && (s.paddingLeft === void 0 || q.boolean(s.paddingLeft)) && (s.paddingRight === void 0 || q.boolean(s.paddingRight));
  }
  e.is = n;
})(Ch || (Ch = {}));
var Fh;
(function(e) {
  function t(n) {
    return { kind: "snippet", value: n };
  }
  e.createSnippet = t;
})(Fh || (Fh = {}));
var _h;
(function(e) {
  function t(n, r, s, i) {
    return { insertText: n, filterText: r, range: s, command: i };
  }
  e.create = t;
})(_h || (_h = {}));
var Th;
(function(e) {
  function t(n) {
    return { items: n };
  }
  e.create = t;
})(Th || (Th = {}));
var Mh;
(function(e) {
  e.Invoked = 0, e.Automatic = 1;
})(Mh || (Mh = {}));
var Oh;
(function(e) {
  function t(n, r) {
    return { range: n, text: r };
  }
  e.create = t;
})(Oh || (Oh = {}));
var Rh;
(function(e) {
  function t(n, r) {
    return { triggerKind: n, selectedCompletionInfo: r };
  }
  e.create = t;
})(Rh || (Rh = {}));
var Ph;
(function(e) {
  function t(n) {
    const r = n;
    return q.objectLiteral(r) && nl.is(r.uri) && q.string(r.name);
  }
  e.is = t;
})(Ph || (Ph = {}));
var Ih;
(function(e) {
  function t(i, a, o, l) {
    return new Ab(i, a, o, l);
  }
  e.create = t;
  function n(i) {
    let a = i;
    return !!(q.defined(a) && q.string(a.uri) && (q.undefined(a.languageId) || q.string(a.languageId)) && q.uinteger(a.lineCount) && q.func(a.getText) && q.func(a.positionAt) && q.func(a.offsetAt));
  }
  e.is = n;
  function r(i, a) {
    let o = i.getText(), l = s(a, (f, c) => {
      let d = f.range.start.line - c.range.start.line;
      return d === 0 ? f.range.start.character - c.range.start.character : d;
    }), u = o.length;
    for (let f = l.length - 1; f >= 0; f--) {
      let c = l[f], d = i.offsetAt(c.range.start), v = i.offsetAt(c.range.end);
      if (v <= u)
        o = o.substring(0, d) + c.newText + o.substring(v, o.length);
      else
        throw new Error("Overlapping edit");
      u = d;
    }
    return o;
  }
  e.applyEdits = r;
  function s(i, a) {
    if (i.length <= 1)
      return i;
    const o = i.length / 2 | 0, l = i.slice(0, o), u = i.slice(o);
    s(l, a), s(u, a);
    let f = 0, c = 0, d = 0;
    for (; f < l.length && c < u.length; )
      a(l[f], u[c]) <= 0 ? i[d++] = l[f++] : i[d++] = u[c++];
    for (; f < l.length; )
      i[d++] = l[f++];
    for (; c < u.length; )
      i[d++] = u[c++];
    return i;
  }
})(Ih || (Ih = {}));
class Ab {
  constructor(t, n, r, s) {
    this._uri = t, this._languageId = n, this._version = r, this._content = s, this._lineOffsets = void 0;
  }
  get uri() {
    return this._uri;
  }
  get languageId() {
    return this._languageId;
  }
  get version() {
    return this._version;
  }
  getText(t) {
    if (t) {
      let n = this.offsetAt(t.start), r = this.offsetAt(t.end);
      return this._content.substring(n, r);
    }
    return this._content;
  }
  update(t, n) {
    this._content = t.text, this._version = n, this._lineOffsets = void 0;
  }
  getLineOffsets() {
    if (this._lineOffsets === void 0) {
      let t = [], n = this._content, r = !0;
      for (let s = 0; s < n.length; s++) {
        r && (t.push(s), r = !1);
        let i = n.charAt(s);
        r = i === "\r" || i === `
`, i === "\r" && s + 1 < n.length && n.charAt(s + 1) === `
` && s++;
      }
      r && n.length > 0 && t.push(n.length), this._lineOffsets = t;
    }
    return this._lineOffsets;
  }
  positionAt(t) {
    t = Math.max(Math.min(t, this._content.length), 0);
    let n = this.getLineOffsets(), r = 0, s = n.length;
    if (s === 0)
      return Ye.create(0, t);
    for (; r < s; ) {
      let a = Math.floor((r + s) / 2);
      n[a] > t ? s = a : r = a + 1;
    }
    let i = r - 1;
    return Ye.create(i, t - n[i]);
  }
  offsetAt(t) {
    let n = this.getLineOffsets();
    if (t.line >= n.length)
      return this._content.length;
    if (t.line < 0)
      return 0;
    let r = n[t.line], s = t.line + 1 < n.length ? n[t.line + 1] : this._content.length;
    return Math.max(Math.min(r + t.character, s), r);
  }
  get lineCount() {
    return this.getLineOffsets().length;
  }
}
var q;
(function(e) {
  const t = Object.prototype.toString;
  function n(v) {
    return typeof v < "u";
  }
  e.defined = n;
  function r(v) {
    return typeof v > "u";
  }
  e.undefined = r;
  function s(v) {
    return v === !0 || v === !1;
  }
  e.boolean = s;
  function i(v) {
    return t.call(v) === "[object String]";
  }
  e.string = i;
  function a(v) {
    return t.call(v) === "[object Number]";
  }
  e.number = a;
  function o(v, D, S) {
    return t.call(v) === "[object Number]" && D <= v && v <= S;
  }
  e.numberRange = o;
  function l(v) {
    return t.call(v) === "[object Number]" && -2147483648 <= v && v <= 2147483647;
  }
  e.integer = l;
  function u(v) {
    return t.call(v) === "[object Number]" && 0 <= v && v <= 2147483647;
  }
  e.uinteger = u;
  function f(v) {
    return t.call(v) === "[object Function]";
  }
  e.func = f;
  function c(v) {
    return v !== null && typeof v == "object";
  }
  e.objectLiteral = c;
  function d(v, D) {
    return Array.isArray(v) && v.every(D);
  }
  e.typedArray = d;
})(q || (q = {}));
const ou = Symbol.for("yaml.alias"), Dl = Symbol.for("yaml.document"), Mn = Symbol.for("yaml.map"), x1 = Symbol.for("yaml.pair"), Qt = Symbol.for("yaml.scalar"), ls = Symbol.for("yaml.seq"), Ct = Symbol.for("yaml.node.type"), $t = (e) => !!e && typeof e == "object" && e[Ct] === ou, us = (e) => !!e && typeof e == "object" && e[Ct] === Dl, Ve = (e) => !!e && typeof e == "object" && e[Ct] === Mn, Ae = (e) => !!e && typeof e == "object" && e[Ct] === x1, ae = (e) => !!e && typeof e == "object" && e[Ct] === Qt, Be = (e) => !!e && typeof e == "object" && e[Ct] === ls;
function Pe(e) {
  if (e && typeof e == "object")
    switch (e[Ct]) {
      case Mn:
      case ls:
        return !0;
    }
  return !1;
}
function De(e) {
  if (e && typeof e == "object")
    switch (e[Ct]) {
      case ou:
      case Mn:
      case Qt:
      case ls:
        return !0;
    }
  return !1;
}
const N1 = (e) => (ae(e) || Pe(e)) && !!e.anchor, Un = Symbol("break visit"), xb = Symbol("skip children"), Os = Symbol("remove node");
function Me(e, t) {
  const n = Nb(t);
  us(e) ? _r(null, e.contents, n, Object.freeze([e])) === Os && (e.contents = null) : _r(null, e, n, Object.freeze([]));
}
Me.BREAK = Un;
Me.SKIP = xb;
Me.REMOVE = Os;
function _r(e, t, n, r) {
  const s = Lb(e, t, n, r);
  if (De(s) || Ae(s))
    return kb(e, r, s), _r(e, s, n, r);
  if (typeof s != "symbol") {
    if (Pe(t)) {
      r = Object.freeze(r.concat(t));
      for (let i = 0; i < t.items.length; ++i) {
        const a = _r(i, t.items[i], n, r);
        if (typeof a == "number")
          i = a - 1;
        else {
          if (a === Un)
            return Un;
          a === Os && (t.items.splice(i, 1), i -= 1);
        }
      }
    } else if (Ae(t)) {
      r = Object.freeze(r.concat(t));
      const i = _r("key", t.key, n, r);
      if (i === Un)
        return Un;
      i === Os && (t.key = null);
      const a = _r("value", t.value, n, r);
      if (a === Un)
        return Un;
      a === Os && (t.value = null);
    }
  }
  return s;
}
function Nb(e) {
  return typeof e == "object" && (e.Collection || e.Node || e.Value) ? Object.assign({
    Alias: e.Node,
    Map: e.Node,
    Scalar: e.Node,
    Seq: e.Node
  }, e.Value && {
    Map: e.Value,
    Scalar: e.Value,
    Seq: e.Value
  }, e.Collection && {
    Map: e.Collection,
    Seq: e.Collection
  }, e) : e;
}
function Lb(e, t, n, r) {
  if (typeof n == "function")
    return n(e, t, r);
  if (Ve(t))
    return n.Map?.(e, t, r);
  if (Be(t))
    return n.Seq?.(e, t, r);
  if (Ae(t))
    return n.Pair?.(e, t, r);
  if (ae(t))
    return n.Scalar?.(e, t, r);
  if ($t(t))
    return n.Alias?.(e, t, r);
}
function kb(e, t, n) {
  const r = t[t.length - 1];
  if (Pe(r))
    r.items[e] = n;
  else if (Ae(r))
    e === "key" ? r.key = n : r.value = n;
  else if (us(r))
    r.contents = n;
  else {
    const s = $t(r) ? "alias" : "scalar";
    throw new Error(`Cannot replace node with ${s} parent`);
  }
}
const Cb = {
  "!": "%21",
  ",": "%2C",
  "[": "%5B",
  "]": "%5D",
  "{": "%7B",
  "}": "%7D"
}, Fb = (e) => e.replace(/[!,[\]{}]/g, (t) => Cb[t]);
class Ze {
  constructor(t, n) {
    this.docStart = null, this.docEnd = !1, this.yaml = Object.assign({}, Ze.defaultYaml, t), this.tags = Object.assign({}, Ze.defaultTags, n);
  }
  clone() {
    const t = new Ze(this.yaml, this.tags);
    return t.docStart = this.docStart, t;
  }
  /**
   * During parsing, get a Directives instance for the current document and
   * update the stream state according to the current version's spec.
   */
  atDocument() {
    const t = new Ze(this.yaml, this.tags);
    switch (this.yaml.version) {
      case "1.1":
        this.atNextDocument = !0;
        break;
      case "1.2":
        this.atNextDocument = !1, this.yaml = {
          explicit: Ze.defaultYaml.explicit,
          version: "1.2"
        }, this.tags = Object.assign({}, Ze.defaultTags);
        break;
    }
    return t;
  }
  /**
   * @param onError - May be called even if the action was successful
   * @returns `true` on success
   */
  add(t, n) {
    this.atNextDocument && (this.yaml = { explicit: Ze.defaultYaml.explicit, version: "1.1" }, this.tags = Object.assign({}, Ze.defaultTags), this.atNextDocument = !1);
    const r = t.trim().split(/[ \t]+/), s = r.shift();
    switch (s) {
      case "%TAG": {
        if (r.length !== 2 && (n(0, "%TAG directive should contain exactly two parts"), r.length < 2))
          return !1;
        const [i, a] = r;
        return this.tags[i] = a, !0;
      }
      case "%YAML": {
        if (this.yaml.explicit = !0, r.length !== 1)
          return n(0, "%YAML directive should contain exactly one part"), !1;
        const [i] = r;
        if (i === "1.1" || i === "1.2")
          return this.yaml.version = i, !0;
        {
          const a = /^\d+\.\d+$/.test(i);
          return n(6, `Unsupported YAML version ${i}`, a), !1;
        }
      }
      default:
        return n(0, `Unknown directive ${s}`, !0), !1;
    }
  }
  /**
   * Resolves a tag, matching handles to those defined in %TAG directives.
   *
   * @returns Resolved tag, which may also be the non-specific tag `'!'` or a
   *   `'!local'` tag, or `null` if unresolvable.
   */
  tagName(t, n) {
    if (t === "!")
      return "!";
    if (t[0] !== "!")
      return n(`Not a valid tag: ${t}`), null;
    if (t[1] === "<") {
      const a = t.slice(2, -1);
      return a === "!" || a === "!!" ? (n(`Verbatim tags aren't resolved, so ${t} is invalid.`), null) : (t[t.length - 1] !== ">" && n("Verbatim tags must end with a >"), a);
    }
    const [, r, s] = t.match(/^(.*!)([^!]*)$/s);
    s || n(`The ${t} tag has no suffix`);
    const i = this.tags[r];
    if (i)
      try {
        return i + decodeURIComponent(s);
      } catch (a) {
        return n(String(a)), null;
      }
    return r === "!" ? t : (n(`Could not resolve tag: ${t}`), null);
  }
  /**
   * Given a fully resolved tag, returns its printable string form,
   * taking into account current tag prefixes and defaults.
   */
  tagString(t) {
    for (const [n, r] of Object.entries(this.tags))
      if (t.startsWith(r))
        return n + Fb(t.substring(r.length));
    return t[0] === "!" ? t : `!<${t}>`;
  }
  toString(t) {
    const n = this.yaml.explicit ? [`%YAML ${this.yaml.version || "1.2"}`] : [], r = Object.entries(this.tags);
    let s;
    if (t && r.length > 0 && De(t.contents)) {
      const i = {};
      Me(t.contents, (a, o) => {
        De(o) && o.tag && (i[o.tag] = !0);
      }), s = Object.keys(i);
    } else
      s = [];
    for (const [i, a] of r)
      i === "!!" && a === "tag:yaml.org,2002:" || (!t || s.some((o) => o.startsWith(a))) && n.push(`%TAG ${i} ${a}`);
    return n.join(`
`);
  }
}
Ze.defaultYaml = { explicit: !1, version: "1.2" };
Ze.defaultTags = { "!!": "tag:yaml.org,2002:" };
function L1(e) {
  if (/[\x00-\x19\s,[\]{}]/.test(e)) {
    const n = `Anchor must not contain whitespace or control characters: ${JSON.stringify(e)}`;
    throw new Error(n);
  }
  return !0;
}
function k1(e) {
  const t = /* @__PURE__ */ new Set();
  return Me(e, {
    Value(n, r) {
      r.anchor && t.add(r.anchor);
    }
  }), t;
}
function C1(e, t) {
  for (let n = 1; ; ++n) {
    const r = `${e}${n}`;
    if (!t.has(r))
      return r;
  }
}
function _b(e, t) {
  const n = [], r = /* @__PURE__ */ new Map();
  let s = null;
  return {
    onAnchor: (i) => {
      n.push(i), s ?? (s = k1(e));
      const a = C1(t, s);
      return s.add(a), a;
    },
    /**
     * With circular references, the source node is only resolved after all
     * of its child nodes are. This is why anchors are set only after all of
     * the nodes have been created.
     */
    setAnchors: () => {
      for (const i of n) {
        const a = r.get(i);
        if (typeof a == "object" && a.anchor && (ae(a.node) || Pe(a.node)))
          a.node.anchor = a.anchor;
        else {
          const o = new Error("Failed to resolve repeated object (this should not happen)");
          throw o.source = i, o;
        }
      }
    },
    sourceObjects: r
  };
}
function Tr(e, t, n, r) {
  if (r && typeof r == "object")
    if (Array.isArray(r))
      for (let s = 0, i = r.length; s < i; ++s) {
        const a = r[s], o = Tr(e, r, String(s), a);
        o === void 0 ? delete r[s] : o !== a && (r[s] = o);
      }
    else if (r instanceof Map)
      for (const s of Array.from(r.keys())) {
        const i = r.get(s), a = Tr(e, r, s, i);
        a === void 0 ? r.delete(s) : a !== i && r.set(s, a);
      }
    else if (r instanceof Set)
      for (const s of Array.from(r)) {
        const i = Tr(e, r, s, s);
        i === void 0 ? r.delete(s) : i !== s && (r.delete(s), r.add(i));
      }
    else
      for (const [s, i] of Object.entries(r)) {
        const a = Tr(e, r, s, i);
        a === void 0 ? delete r[s] : a !== i && (r[s] = a);
      }
  return e.call(t, n, r);
}
function kt(e, t, n) {
  if (Array.isArray(e))
    return e.map((r, s) => kt(r, String(s), n));
  if (e && typeof e.toJSON == "function") {
    if (!n || !N1(e))
      return e.toJSON(t, n);
    const r = { aliasCount: 0, count: 1, res: void 0 };
    n.anchors.set(e, r), n.onCreate = (i) => {
      r.res = i, delete n.onCreate;
    };
    const s = e.toJSON(t, n);
    return n.onCreate && n.onCreate(s), s;
  }
  return typeof e == "bigint" && !n?.keep ? Number(e) : e;
}
class lu {
  constructor(t) {
    Object.defineProperty(this, Ct, { value: t });
  }
  /** Create a copy of this node.  */
  clone() {
    const t = Object.create(Object.getPrototypeOf(this), Object.getOwnPropertyDescriptors(this));
    return this.range && (t.range = this.range.slice()), t;
  }
  /** A plain JavaScript representation of this node. */
  toJS(t, { mapAsMap: n, maxAliasCount: r, onAnchor: s, reviver: i } = {}) {
    if (!us(t))
      throw new TypeError("A document argument is required");
    const a = {
      anchors: /* @__PURE__ */ new Map(),
      doc: t,
      keep: !0,
      mapAsMap: n === !0,
      mapKeyWarned: !1,
      maxAliasCount: typeof r == "number" ? r : 100
    }, o = kt(this, "", a);
    if (typeof s == "function")
      for (const { count: l, res: u } of a.anchors.values())
        s(u, l);
    return typeof i == "function" ? Tr(i, { "": o }, "", o) : o;
  }
}
class uu extends lu {
  constructor(t) {
    super(ou), this.source = t, Object.defineProperty(this, "tag", {
      set() {
        throw new Error("Alias nodes cannot have tags");
      }
    });
  }
  /**
   * Resolve the value of this alias within `doc`, finding the last
   * instance of the `source` anchor before this node.
   */
  resolve(t, n) {
    let r;
    n?.aliasResolveCache ? r = n.aliasResolveCache : (r = [], Me(t, {
      Node: (i, a) => {
        ($t(a) || N1(a)) && r.push(a);
      }
    }), n && (n.aliasResolveCache = r));
    let s;
    for (const i of r) {
      if (i === this)
        break;
      i.anchor === this.source && (s = i);
    }
    return s;
  }
  toJSON(t, n) {
    if (!n)
      return { source: this.source };
    const { anchors: r, doc: s, maxAliasCount: i } = n, a = this.resolve(s, n);
    if (!a) {
      const l = `Unresolved alias (the anchor must be set before the alias): ${this.source}`;
      throw new ReferenceError(l);
    }
    let o = r.get(a);
    if (o || (kt(a, null, n), o = r.get(a)), !o || o.res === void 0) {
      const l = "This should not happen: Alias anchor was not resolved?";
      throw new ReferenceError(l);
    }
    if (i >= 0 && (o.count += 1, o.aliasCount === 0 && (o.aliasCount = _i(s, a, r)), o.count * o.aliasCount > i)) {
      const l = "Excessive alias count indicates a resource exhaustion attack";
      throw new ReferenceError(l);
    }
    return o.res;
  }
  toString(t, n, r) {
    const s = `*${this.source}`;
    if (t) {
      if (L1(this.source), t.options.verifyAliasOrder && !t.anchors.has(this.source)) {
        const i = `Unresolved alias (the anchor must be set before the alias): ${this.source}`;
        throw new Error(i);
      }
      if (t.implicitKey)
        return `${s} `;
    }
    return s;
  }
}
function _i(e, t, n) {
  if ($t(t)) {
    const r = t.resolve(e), s = n && r && n.get(r);
    return s ? s.count * s.aliasCount : 0;
  } else if (Pe(t)) {
    let r = 0;
    for (const s of t.items) {
      const i = _i(e, s, n);
      i > r && (r = i);
    }
    return r;
  } else if (Ae(t)) {
    const r = _i(e, t.key, n), s = _i(e, t.value, n);
    return Math.max(r, s);
  }
  return 1;
}
const F1 = (e) => !e || typeof e != "function" && typeof e != "object";
class oe extends lu {
  constructor(t) {
    super(Qt), this.value = t;
  }
  toJSON(t, n) {
    return n?.keep ? this.value : kt(this.value, t, n);
  }
  toString() {
    return String(this.value);
  }
}
oe.BLOCK_FOLDED = "BLOCK_FOLDED";
oe.BLOCK_LITERAL = "BLOCK_LITERAL";
oe.PLAIN = "PLAIN";
oe.QUOTE_DOUBLE = "QUOTE_DOUBLE";
oe.QUOTE_SINGLE = "QUOTE_SINGLE";
const Tb = "tag:yaml.org,2002:";
function Mb(e, t, n) {
  if (t) {
    const r = n.filter((i) => i.tag === t), s = r.find((i) => !i.format) ?? r[0];
    if (!s)
      throw new Error(`Tag ${t} not found`);
    return s;
  }
  return n.find((r) => r.identify?.(e) && !r.format);
}
function Ks(e, t, n) {
  if (us(e) && (e = e.contents), De(e))
    return e;
  if (Ae(e)) {
    const c = n.schema[Mn].createNode?.(n.schema, null, n);
    return c.items.push(e), c;
  }
  (e instanceof String || e instanceof Number || e instanceof Boolean || typeof BigInt < "u" && e instanceof BigInt) && (e = e.valueOf());
  const { aliasDuplicateObjects: r, onAnchor: s, onTagObj: i, schema: a, sourceObjects: o } = n;
  let l;
  if (r && e && typeof e == "object") {
    if (l = o.get(e), l)
      return l.anchor ?? (l.anchor = s(e)), new uu(l.anchor);
    l = { anchor: null, node: null }, o.set(e, l);
  }
  t?.startsWith("!!") && (t = Tb + t.slice(2));
  let u = Mb(e, t, a.tags);
  if (!u) {
    if (e && typeof e.toJSON == "function" && (e = e.toJSON()), !e || typeof e != "object") {
      const c = new oe(e);
      return l && (l.node = c), c;
    }
    u = e instanceof Map ? a[Mn] : Symbol.iterator in Object(e) ? a[ls] : a[Mn];
  }
  i && (i(u), delete n.onTagObj);
  const f = u?.createNode ? u.createNode(n.schema, e, n) : typeof u?.nodeClass?.from == "function" ? u.nodeClass.from(n.schema, e, n) : new oe(e);
  return t ? f.tag = t : u.default || (f.tag = u.tag), l && (l.node = f), f;
}
function aa(e, t, n) {
  let r = n;
  for (let s = t.length - 1; s >= 0; --s) {
    const i = t[s];
    if (typeof i == "number" && Number.isInteger(i) && i >= 0) {
      const a = [];
      a[i] = r, r = a;
    } else
      r = /* @__PURE__ */ new Map([[i, r]]);
  }
  return Ks(r, void 0, {
    aliasDuplicateObjects: !1,
    keepUndefined: !1,
    onAnchor: () => {
      throw new Error("This should not happen, please report a bug.");
    },
    schema: e,
    sourceObjects: /* @__PURE__ */ new Map()
  });
}
const Ls = (e) => e == null || typeof e == "object" && !!e[Symbol.iterator]().next().done;
class _1 extends lu {
  constructor(t, n) {
    super(t), Object.defineProperty(this, "schema", {
      value: n,
      configurable: !0,
      enumerable: !1,
      writable: !0
    });
  }
  /**
   * Create a copy of this collection.
   *
   * @param schema - If defined, overwrites the original's schema
   */
  clone(t) {
    const n = Object.create(Object.getPrototypeOf(this), Object.getOwnPropertyDescriptors(this));
    return t && (n.schema = t), n.items = n.items.map((r) => De(r) || Ae(r) ? r.clone(t) : r), this.range && (n.range = this.range.slice()), n;
  }
  /**
   * Adds a value to the collection. For `!!map` and `!!omap` the value must
   * be a Pair instance or a `{ key, value }` object, which may not have a key
   * that already exists in the map.
   */
  addIn(t, n) {
    if (Ls(t))
      this.add(n);
    else {
      const [r, ...s] = t, i = this.get(r, !0);
      if (Pe(i))
        i.addIn(s, n);
      else if (i === void 0 && this.schema)
        this.set(r, aa(this.schema, s, n));
      else
        throw new Error(`Expected YAML collection at ${r}. Remaining path: ${s}`);
    }
  }
  /**
   * Removes a value from the collection.
   * @returns `true` if the item was found and removed.
   */
  deleteIn(t) {
    const [n, ...r] = t;
    if (r.length === 0)
      return this.delete(n);
    const s = this.get(n, !0);
    if (Pe(s))
      return s.deleteIn(r);
    throw new Error(`Expected YAML collection at ${n}. Remaining path: ${r}`);
  }
  /**
   * Returns item at `key`, or `undefined` if not found. By default unwraps
   * scalar values from their surrounding node; to disable set `keepScalar` to
   * `true` (collections are always returned intact).
   */
  getIn(t, n) {
    const [r, ...s] = t, i = this.get(r, !0);
    return s.length === 0 ? !n && ae(i) ? i.value : i : Pe(i) ? i.getIn(s, n) : void 0;
  }
  hasAllNullValues(t) {
    return this.items.every((n) => {
      if (!Ae(n))
        return !1;
      const r = n.value;
      return r == null || t && ae(r) && r.value == null && !r.commentBefore && !r.comment && !r.tag;
    });
  }
  /**
   * Checks if the collection includes a value with the key `key`.
   */
  hasIn(t) {
    const [n, ...r] = t;
    if (r.length === 0)
      return this.has(n);
    const s = this.get(n, !0);
    return Pe(s) ? s.hasIn(r) : !1;
  }
  /**
   * Sets a value in this collection. For `!!set`, `value` needs to be a
   * boolean to add/remove the item from the set.
   */
  setIn(t, n) {
    const [r, ...s] = t;
    if (s.length === 0)
      this.set(r, n);
    else {
      const i = this.get(r, !0);
      if (Pe(i))
        i.setIn(s, n);
      else if (i === void 0 && this.schema)
        this.set(r, aa(this.schema, s, n));
      else
        throw new Error(`Expected YAML collection at ${r}. Remaining path: ${s}`);
    }
  }
}
const Ob = (e) => e.replace(/^(?!$)(?: $)?/gm, "#");
function un(e, t) {
  return /^\n+$/.test(e) ? e.substring(1) : t ? e.replace(/^(?! *$)/gm, t) : e;
}
const Kn = (e, t, n) => e.endsWith(`
`) ? un(n, t) : n.includes(`
`) ? `
` + un(n, t) : (e.endsWith(" ") ? "" : " ") + n, T1 = "flow", Sl = "block", Ti = "quoted";
function xa(e, t, n = "flow", { indentAtStart: r, lineWidth: s = 80, minContentWidth: i = 20, onFold: a, onOverflow: o } = {}) {
  if (!s || s < 0)
    return e;
  s < i && (i = 0);
  const l = Math.max(1 + i, 1 + s - t.length);
  if (e.length <= l)
    return e;
  const u = [], f = {};
  let c = s - t.length;
  typeof r == "number" && (r > s - Math.max(2, i) ? u.push(0) : c = s - r);
  let d, v, D = !1, S = -1, x = -1, N = -1;
  n === Sl && (S = $h(e, S, t.length), S !== -1 && (c = S + l));
  for (let y; y = e[S += 1]; ) {
    if (n === Ti && y === "\\") {
      switch (x = S, e[S + 1]) {
        case "x":
          S += 3;
          break;
        case "u":
          S += 5;
          break;
        case "U":
          S += 9;
          break;
        default:
          S += 1;
      }
      N = S;
    }
    if (y === `
`)
      n === Sl && (S = $h(e, S, t.length)), c = S + t.length + l, d = void 0;
    else {
      if (y === " " && v && v !== " " && v !== `
` && v !== "	") {
        const b = e[S + 1];
        b && b !== " " && b !== `
` && b !== "	" && (d = S);
      }
      if (S >= c)
        if (d)
          u.push(d), c = d + l, d = void 0;
        else if (n === Ti) {
          for (; v === " " || v === "	"; )
            v = y, y = e[S += 1], D = !0;
          const b = S > N + 1 ? S - 2 : x - 1;
          if (f[b])
            return e;
          u.push(b), f[b] = !0, c = b + l, d = void 0;
        } else
          D = !0;
    }
    v = y;
  }
  if (D && o && o(), u.length === 0)
    return e;
  a && a();
  let k = e.slice(0, u[0]);
  for (let y = 0; y < u.length; ++y) {
    const b = u[y], h = u[y + 1] || e.length;
    b === 0 ? k = `
${t}${e.slice(0, h)}` : (n === Ti && f[b] && (k += `${e[b]}\\`), k += `
${t}${e.slice(b + 1, h)}`);
  }
  return k;
}
function $h(e, t, n) {
  let r = t, s = t + 1, i = e[s];
  for (; i === " " || i === "	"; )
    if (t < s + n)
      i = e[++t];
    else {
      do
        i = e[++t];
      while (i && i !== `
`);
      r = t, s = t + 1, i = e[s];
    }
  return r;
}
const Na = (e, t) => ({
  indentAtStart: t ? e.indent.length : e.indentAtStart,
  lineWidth: e.options.lineWidth,
  minContentWidth: e.options.minContentWidth
}), La = (e) => /^(%|---|\.\.\.)/m.test(e);
function Rb(e, t, n) {
  if (!t || t < 0)
    return !1;
  const r = t - n, s = e.length;
  if (s <= r)
    return !1;
  for (let i = 0, a = 0; i < s; ++i)
    if (e[i] === `
`) {
      if (i - a > r)
        return !0;
      if (a = i + 1, s - a <= r)
        return !1;
    }
  return !0;
}
function Rs(e, t) {
  const n = JSON.stringify(e);
  if (t.options.doubleQuotedAsJSON)
    return n;
  const { implicitKey: r } = t, s = t.options.doubleQuotedMinMultiLineLength, i = t.indent || (La(e) ? "  " : "");
  let a = "", o = 0;
  for (let l = 0, u = n[l]; u; u = n[++l])
    if (u === " " && n[l + 1] === "\\" && n[l + 2] === "n" && (a += n.slice(o, l) + "\\ ", l += 1, o = l, u = "\\"), u === "\\")
      switch (n[l + 1]) {
        case "u":
          {
            a += n.slice(o, l);
            const f = n.substr(l + 2, 4);
            switch (f) {
              case "0000":
                a += "\\0";
                break;
              case "0007":
                a += "\\a";
                break;
              case "000b":
                a += "\\v";
                break;
              case "001b":
                a += "\\e";
                break;
              case "0085":
                a += "\\N";
                break;
              case "00a0":
                a += "\\_";
                break;
              case "2028":
                a += "\\L";
                break;
              case "2029":
                a += "\\P";
                break;
              default:
                f.substr(0, 2) === "00" ? a += "\\x" + f.substr(2) : a += n.substr(l, 6);
            }
            l += 5, o = l + 1;
          }
          break;
        case "n":
          if (r || n[l + 2] === '"' || n.length < s)
            l += 1;
          else {
            for (a += n.slice(o, l) + `

`; n[l + 2] === "\\" && n[l + 3] === "n" && n[l + 4] !== '"'; )
              a += `
`, l += 2;
            a += i, n[l + 2] === " " && (a += "\\"), l += 1, o = l + 1;
          }
          break;
        default:
          l += 1;
      }
  return a = o ? a + n.slice(o) : n, r ? a : xa(a, i, Ti, Na(t, !1));
}
function El(e, t) {
  if (t.options.singleQuote === !1 || t.implicitKey && e.includes(`
`) || /[ \t]\n|\n[ \t]/.test(e))
    return Rs(e, t);
  const n = t.indent || (La(e) ? "  " : ""), r = "'" + e.replace(/'/g, "''").replace(/\n+/g, `$&
${n}`) + "'";
  return t.implicitKey ? r : xa(r, n, T1, Na(t, !1));
}
function Mr(e, t) {
  const { singleQuote: n } = t.options;
  let r;
  if (n === !1)
    r = Rs;
  else {
    const s = e.includes('"'), i = e.includes("'");
    s && !i ? r = El : i && !s ? r = Rs : r = n ? El : Rs;
  }
  return r(e, t);
}
let Al;
try {
  Al = new RegExp(`(^|(?<!
))
+(?!
|$)`, "g");
} catch {
  Al = /\n+(?!\n|$)/g;
}
function Mi({ comment: e, type: t, value: n }, r, s, i) {
  const { blockQuote: a, commentString: o, lineWidth: l } = r.options;
  if (!a || /\n[\t ]+$/.test(n))
    return Mr(n, r);
  const u = r.indent || (r.forceBlockIndent || La(n) ? "  " : ""), f = a === "literal" ? !0 : a === "folded" || t === oe.BLOCK_FOLDED ? !1 : t === oe.BLOCK_LITERAL ? !0 : !Rb(n, l, u.length);
  if (!n)
    return f ? `|
` : `>
`;
  let c, d;
  for (d = n.length; d > 0; --d) {
    const h = n[d - 1];
    if (h !== `
` && h !== "	" && h !== " ")
      break;
  }
  let v = n.substring(d);
  const D = v.indexOf(`
`);
  D === -1 ? c = "-" : n === v || D !== v.length - 1 ? (c = "+", i && i()) : c = "", v && (n = n.slice(0, -v.length), v[v.length - 1] === `
` && (v = v.slice(0, -1)), v = v.replace(Al, `$&${u}`));
  let S = !1, x, N = -1;
  for (x = 0; x < n.length; ++x) {
    const h = n[x];
    if (h === " ")
      S = !0;
    else if (h === `
`)
      N = x;
    else
      break;
  }
  let k = n.substring(0, N < x ? N + 1 : x);
  k && (n = n.substring(k.length), k = k.replace(/\n+/g, `$&${u}`));
  let b = (S ? u ? "2" : "1" : "") + c;
  if (e && (b += " " + o(e.replace(/ ?[\r\n]+/g, " ")), s && s()), !f) {
    const h = n.replace(/\n+/g, `
$&`).replace(/(?:^|\n)([\t ].*)(?:([\n\t ]*)\n(?![\n\t ]))?/g, "$1$2").replace(/\n+/g, `$&${u}`);
    let m = !1;
    const p = Na(r, !0);
    a !== "folded" && t !== oe.BLOCK_FOLDED && (p.onOverflow = () => {
      m = !0;
    });
    const E = xa(`${k}${h}${v}`, u, Sl, p);
    if (!m)
      return `>${b}
${u}${E}`;
  }
  return n = n.replace(/\n+/g, `$&${u}`), `|${b}
${u}${k}${n}${v}`;
}
function Pb(e, t, n, r) {
  const { type: s, value: i } = e, { actualString: a, implicitKey: o, indent: l, indentStep: u, inFlow: f } = t;
  if (o && i.includes(`
`) || f && /[[\]{},]/.test(i))
    return Mr(i, t);
  if (/^[\n\t ,[\]{}#&*!|>'"%@`]|^[?-]$|^[?-][ \t]|[\n:][ \t]|[ \t]\n|[\n\t ]#|[\n\t :]$/.test(i))
    return o || f || !i.includes(`
`) ? Mr(i, t) : Mi(e, t, n, r);
  if (!o && !f && s !== oe.PLAIN && i.includes(`
`))
    return Mi(e, t, n, r);
  if (La(i)) {
    if (l === "")
      return t.forceBlockIndent = !0, Mi(e, t, n, r);
    if (o && l === u)
      return Mr(i, t);
  }
  const c = i.replace(/\n+/g, `$&
${l}`);
  if (a) {
    const d = (S) => S.default && S.tag !== "tag:yaml.org,2002:str" && S.test?.test(c), { compat: v, tags: D } = t.doc.schema;
    if (D.some(d) || v?.some(d))
      return Mr(i, t);
  }
  return o ? c : xa(c, l, T1, Na(t, !1));
}
function cu(e, t, n, r) {
  const { implicitKey: s, inFlow: i } = t, a = typeof e.value == "string" ? e : Object.assign({}, e, { value: String(e.value) });
  let { type: o } = e;
  o !== oe.QUOTE_DOUBLE && /[\x00-\x08\x0b-\x1f\x7f-\x9f\u{D800}-\u{DFFF}]/u.test(a.value) && (o = oe.QUOTE_DOUBLE);
  const l = (f) => {
    switch (f) {
      case oe.BLOCK_FOLDED:
      case oe.BLOCK_LITERAL:
        return s || i ? Mr(a.value, t) : Mi(a, t, n, r);
      case oe.QUOTE_DOUBLE:
        return Rs(a.value, t);
      case oe.QUOTE_SINGLE:
        return El(a.value, t);
      case oe.PLAIN:
        return Pb(a, t, n, r);
      default:
        return null;
    }
  };
  let u = l(o);
  if (u === null) {
    const { defaultKeyType: f, defaultStringType: c } = t.options, d = s && f || c;
    if (u = l(d), u === null)
      throw new Error(`Unsupported default string type ${d}`);
  }
  return u;
}
function M1(e, t) {
  const n = Object.assign({
    blockQuote: !0,
    commentString: Ob,
    defaultKeyType: null,
    defaultStringType: "PLAIN",
    directives: null,
    doubleQuotedAsJSON: !1,
    doubleQuotedMinMultiLineLength: 40,
    falseStr: "false",
    flowCollectionPadding: !0,
    indentSeq: !0,
    lineWidth: 80,
    minContentWidth: 20,
    nullStr: "null",
    simpleKeys: !1,
    singleQuote: null,
    trueStr: "true",
    verifyAliasOrder: !0
  }, e.schema.toStringOptions, t);
  let r;
  switch (n.collectionStyle) {
    case "block":
      r = !1;
      break;
    case "flow":
      r = !0;
      break;
    default:
      r = null;
  }
  return {
    anchors: /* @__PURE__ */ new Set(),
    doc: e,
    flowCollectionPadding: n.flowCollectionPadding ? " " : "",
    indent: "",
    indentStep: typeof n.indent == "number" ? " ".repeat(n.indent) : "  ",
    inFlow: r,
    options: n
  };
}
function Ib(e, t) {
  if (t.tag) {
    const s = e.filter((i) => i.tag === t.tag);
    if (s.length > 0)
      return s.find((i) => i.format === t.format) ?? s[0];
  }
  let n, r;
  if (ae(t)) {
    r = t.value;
    let s = e.filter((i) => i.identify?.(r));
    if (s.length > 1) {
      const i = s.filter((a) => a.test);
      i.length > 0 && (s = i);
    }
    n = s.find((i) => i.format === t.format) ?? s.find((i) => !i.format);
  } else
    r = t, n = e.find((s) => s.nodeClass && r instanceof s.nodeClass);
  if (!n) {
    const s = r?.constructor?.name ?? (r === null ? "null" : typeof r);
    throw new Error(`Tag not resolved for ${s} value`);
  }
  return n;
}
function $b(e, t, { anchors: n, doc: r }) {
  if (!r.directives)
    return "";
  const s = [], i = (ae(e) || Pe(e)) && e.anchor;
  i && L1(i) && (n.add(i), s.push(`&${i}`));
  const a = e.tag ?? (t.default ? null : t.tag);
  return a && s.push(r.directives.tagString(a)), s.join(" ");
}
function rs(e, t, n, r) {
  if (Ae(e))
    return e.toString(t, n, r);
  if ($t(e)) {
    if (t.doc.directives)
      return e.toString(t);
    if (t.resolvedAliases?.has(e))
      throw new TypeError("Cannot stringify circular structure without alias nodes");
    t.resolvedAliases ? t.resolvedAliases.add(e) : t.resolvedAliases = /* @__PURE__ */ new Set([e]), e = e.resolve(t.doc);
  }
  let s;
  const i = De(e) ? e : t.doc.createNode(e, { onTagObj: (l) => s = l });
  s ?? (s = Ib(t.doc.schema.tags, i));
  const a = $b(i, s, t);
  a.length > 0 && (t.indentAtStart = (t.indentAtStart ?? 0) + a.length + 1);
  const o = typeof s.stringify == "function" ? s.stringify(i, t, n, r) : ae(i) ? cu(i, t, n, r) : i.toString(t, n, r);
  return a ? ae(i) || o[0] === "{" || o[0] === "[" ? `${a} ${o}` : `${a}
${t.indent}${o}` : o;
}
function Bb({ key: e, value: t }, n, r, s) {
  const { allNullValues: i, doc: a, indent: o, indentStep: l, options: { commentString: u, indentSeq: f, simpleKeys: c } } = n;
  let d = De(e) && e.comment || null;
  if (c) {
    if (d)
      throw new Error("With simple keys, key nodes cannot have comments");
    if (Pe(e) || !De(e) && typeof e == "object") {
      const p = "With simple keys, collection cannot be used as a key value";
      throw new Error(p);
    }
  }
  let v = !c && (!e || d && t == null && !n.inFlow || Pe(e) || (ae(e) ? e.type === oe.BLOCK_FOLDED || e.type === oe.BLOCK_LITERAL : typeof e == "object"));
  n = Object.assign({}, n, {
    allNullValues: !1,
    implicitKey: !v && (c || !i),
    indent: o + l
  });
  let D = !1, S = !1, x = rs(e, n, () => D = !0, () => S = !0);
  if (!v && !n.inFlow && x.length > 1024) {
    if (c)
      throw new Error("With simple keys, single line scalar must not span more than 1024 characters");
    v = !0;
  }
  if (n.inFlow) {
    if (i || t == null)
      return D && r && r(), x === "" ? "?" : v ? `? ${x}` : x;
  } else if (i && !c || t == null && v)
    return x = `? ${x}`, d && !D ? x += Kn(x, n.indent, u(d)) : S && s && s(), x;
  D && (d = null), v ? (d && (x += Kn(x, n.indent, u(d))), x = `? ${x}
${o}:`) : (x = `${x}:`, d && (x += Kn(x, n.indent, u(d))));
  let N, k, y;
  De(t) ? (N = !!t.spaceBefore, k = t.commentBefore, y = t.comment) : (N = !1, k = null, y = null, t && typeof t == "object" && (t = a.createNode(t))), n.implicitKey = !1, !v && !d && ae(t) && (n.indentAtStart = x.length + 1), S = !1, !f && l.length >= 2 && !n.inFlow && !v && Be(t) && !t.flow && !t.tag && !t.anchor && (n.indent = n.indent.substring(2));
  let b = !1;
  const h = rs(t, n, () => b = !0, () => S = !0);
  let m = " ";
  if (d || N || k) {
    if (m = N ? `
` : "", k) {
      const p = u(k);
      m += `
${un(p, n.indent)}`;
    }
    h === "" && !n.inFlow ? m === `
` && (m = `

`) : m += `
${n.indent}`;
  } else if (!v && Pe(t)) {
    const p = h[0], E = h.indexOf(`
`), w = E !== -1, L = n.inFlow ?? t.flow ?? t.items.length === 0;
    if (w || !L) {
      let C = !1;
      if (w && (p === "&" || p === "!")) {
        let A = h.indexOf(" ");
        p === "&" && A !== -1 && A < E && h[A + 1] === "!" && (A = h.indexOf(" ", A + 1)), (A === -1 || E < A) && (C = !0);
      }
      C || (m = `
${n.indent}`);
    }
  } else (h === "" || h[0] === `
`) && (m = "");
  return x += m + h, n.inFlow ? b && r && r() : y && !b ? x += Kn(x, n.indent, u(y)) : S && s && s(), x;
}
function O1(e, t) {
  (e === "debug" || e === "warn") && console.warn(t);
}
const hi = "<<", dn = {
  identify: (e) => e === hi || typeof e == "symbol" && e.description === hi,
  default: "key",
  tag: "tag:yaml.org,2002:merge",
  test: /^<<$/,
  resolve: () => Object.assign(new oe(Symbol(hi)), {
    addToJSMap: R1
  }),
  stringify: () => hi
}, Vb = (e, t) => (dn.identify(t) || ae(t) && (!t.type || t.type === oe.PLAIN) && dn.identify(t.value)) && e?.doc.schema.tags.some((n) => n.tag === dn.tag && n.default);
function R1(e, t, n) {
  if (n = e && $t(n) ? n.resolve(e.doc) : n, Be(n))
    for (const r of n.items)
      eo(e, t, r);
  else if (Array.isArray(n))
    for (const r of n)
      eo(e, t, r);
  else
    eo(e, t, n);
}
function eo(e, t, n) {
  const r = e && $t(n) ? n.resolve(e.doc) : n;
  if (!Ve(r))
    throw new Error("Merge sources must be maps or map aliases");
  const s = r.toJSON(null, e, Map);
  for (const [i, a] of s)
    t instanceof Map ? t.has(i) || t.set(i, a) : t instanceof Set ? t.add(i) : Object.prototype.hasOwnProperty.call(t, i) || Object.defineProperty(t, i, {
      value: a,
      writable: !0,
      enumerable: !0,
      configurable: !0
    });
  return t;
}
function P1(e, t, { key: n, value: r }) {
  if (De(n) && n.addToJSMap)
    n.addToJSMap(e, t, r);
  else if (Vb(e, n))
    R1(e, t, r);
  else {
    const s = kt(n, "", e);
    if (t instanceof Map)
      t.set(s, kt(r, s, e));
    else if (t instanceof Set)
      t.add(s);
    else {
      const i = jb(n, s, e), a = kt(r, i, e);
      i in t ? Object.defineProperty(t, i, {
        value: a,
        writable: !0,
        enumerable: !0,
        configurable: !0
      }) : t[i] = a;
    }
  }
  return t;
}
function jb(e, t, n) {
  if (t === null)
    return "";
  if (typeof t != "object")
    return String(t);
  if (De(e) && n?.doc) {
    const r = M1(n.doc, {});
    r.anchors = /* @__PURE__ */ new Set();
    for (const i of n.anchors.keys())
      r.anchors.add(i.anchor);
    r.inFlow = !0, r.inStringifyKey = !0;
    const s = e.toString(r);
    if (!n.mapKeyWarned) {
      let i = JSON.stringify(s);
      i.length > 40 && (i = i.substring(0, 36) + '..."'), O1(n.doc.options.logLevel, `Keys with collection values will be stringified due to JS Object restrictions: ${i}. Set mapAsMap: true to use object keys.`), n.mapKeyWarned = !0;
    }
    return s;
  }
  return JSON.stringify(t);
}
function fu(e, t, n) {
  const r = Ks(e, void 0, n), s = Ks(t, void 0, n);
  return new tt(r, s);
}
class tt {
  constructor(t, n = null) {
    Object.defineProperty(this, Ct, { value: x1 }), this.key = t, this.value = n;
  }
  clone(t) {
    let { key: n, value: r } = this;
    return De(n) && (n = n.clone(t)), De(r) && (r = r.clone(t)), new tt(n, r);
  }
  toJSON(t, n) {
    const r = n?.mapAsMap ? /* @__PURE__ */ new Map() : {};
    return P1(n, r, this);
  }
  toString(t, n, r) {
    return t?.doc ? Bb(this, t, n, r) : JSON.stringify(this);
  }
}
function I1(e, t, n) {
  return (t.inFlow ?? e.flow ? qb : Ub)(e, t, n);
}
function Ub({ comment: e, items: t }, n, { blockItemPrefix: r, flowChars: s, itemIndent: i, onChompKeep: a, onComment: o }) {
  const { indent: l, options: { commentString: u } } = n, f = Object.assign({}, n, { indent: i, type: null });
  let c = !1;
  const d = [];
  for (let D = 0; D < t.length; ++D) {
    const S = t[D];
    let x = null;
    if (De(S))
      !c && S.spaceBefore && d.push(""), oa(n, d, S.commentBefore, c), S.comment && (x = S.comment);
    else if (Ae(S)) {
      const k = De(S.key) ? S.key : null;
      k && (!c && k.spaceBefore && d.push(""), oa(n, d, k.commentBefore, c));
    }
    c = !1;
    let N = rs(S, f, () => x = null, () => c = !0);
    x && (N += Kn(N, i, u(x))), c && x && (c = !1), d.push(r + N);
  }
  let v;
  if (d.length === 0)
    v = s.start + s.end;
  else {
    v = d[0];
    for (let D = 1; D < d.length; ++D) {
      const S = d[D];
      v += S ? `
${l}${S}` : `
`;
    }
  }
  return e ? (v += `
` + un(u(e), l), o && o()) : c && a && a(), v;
}
function qb({ items: e }, t, { flowChars: n, itemIndent: r }) {
  const { indent: s, indentStep: i, flowCollectionPadding: a, options: { commentString: o } } = t;
  r += i;
  const l = Object.assign({}, t, {
    indent: r,
    inFlow: !0,
    type: null
  });
  let u = !1, f = 0;
  const c = [];
  for (let D = 0; D < e.length; ++D) {
    const S = e[D];
    let x = null;
    if (De(S))
      S.spaceBefore && c.push(""), oa(t, c, S.commentBefore, !1), S.comment && (x = S.comment);
    else if (Ae(S)) {
      const k = De(S.key) ? S.key : null;
      k && (k.spaceBefore && c.push(""), oa(t, c, k.commentBefore, !1), k.comment && (u = !0));
      const y = De(S.value) ? S.value : null;
      y ? (y.comment && (x = y.comment), y.commentBefore && (u = !0)) : S.value == null && k?.comment && (x = k.comment);
    }
    x && (u = !0);
    let N = rs(S, l, () => x = null);
    D < e.length - 1 && (N += ","), x && (N += Kn(N, r, o(x))), !u && (c.length > f || N.includes(`
`)) && (u = !0), c.push(N), f = c.length;
  }
  const { start: d, end: v } = n;
  if (c.length === 0)
    return d + v;
  if (!u) {
    const D = c.reduce((S, x) => S + x.length + 2, 2);
    u = t.options.lineWidth > 0 && D > t.options.lineWidth;
  }
  if (u) {
    let D = d;
    for (const S of c)
      D += S ? `
${i}${s}${S}` : `
`;
    return `${D}
${s}${v}`;
  } else
    return `${d}${a}${c.join(" ")}${a}${v}`;
}
function oa({ indent: e, options: { commentString: t } }, n, r, s) {
  if (r && s && (r = r.replace(/^\n+/, "")), r) {
    const i = un(t(r), e);
    n.push(i.trimStart());
  }
}
function Xn(e, t) {
  const n = ae(t) ? t.value : t;
  for (const r of e)
    if (Ae(r) && (r.key === t || r.key === n || ae(r.key) && r.key.value === n))
      return r;
}
class xt extends _1 {
  static get tagName() {
    return "tag:yaml.org,2002:map";
  }
  constructor(t) {
    super(Mn, t), this.items = [];
  }
  /**
   * A generic collection parsing method that can be extended
   * to other node classes that inherit from YAMLMap
   */
  static from(t, n, r) {
    const { keepUndefined: s, replacer: i } = r, a = new this(t), o = (l, u) => {
      if (typeof i == "function")
        u = i.call(n, l, u);
      else if (Array.isArray(i) && !i.includes(l))
        return;
      (u !== void 0 || s) && a.items.push(fu(l, u, r));
    };
    if (n instanceof Map)
      for (const [l, u] of n)
        o(l, u);
    else if (n && typeof n == "object")
      for (const l of Object.keys(n))
        o(l, n[l]);
    return typeof t.sortMapEntries == "function" && a.items.sort(t.sortMapEntries), a;
  }
  /**
   * Adds a value to the collection.
   *
   * @param overwrite - If not set `true`, using a key that is already in the
   *   collection will throw. Otherwise, overwrites the previous value.
   */
  add(t, n) {
    let r;
    Ae(t) ? r = t : !t || typeof t != "object" || !("key" in t) ? r = new tt(t, t?.value) : r = new tt(t.key, t.value);
    const s = Xn(this.items, r.key), i = this.schema?.sortMapEntries;
    if (s) {
      if (!n)
        throw new Error(`Key ${r.key} already set`);
      ae(s.value) && F1(r.value) ? s.value.value = r.value : s.value = r.value;
    } else if (i) {
      const a = this.items.findIndex((o) => i(r, o) < 0);
      a === -1 ? this.items.push(r) : this.items.splice(a, 0, r);
    } else
      this.items.push(r);
  }
  delete(t) {
    const n = Xn(this.items, t);
    return n ? this.items.splice(this.items.indexOf(n), 1).length > 0 : !1;
  }
  get(t, n) {
    const s = Xn(this.items, t)?.value;
    return (!n && ae(s) ? s.value : s) ?? void 0;
  }
  has(t) {
    return !!Xn(this.items, t);
  }
  set(t, n) {
    this.add(new tt(t, n), !0);
  }
  /**
   * @param ctx - Conversion context, originally set in Document#toJS()
   * @param {Class} Type - If set, forces the returned collection type
   * @returns Instance of Type, Map, or Object
   */
  toJSON(t, n, r) {
    const s = r ? new r() : n?.mapAsMap ? /* @__PURE__ */ new Map() : {};
    n?.onCreate && n.onCreate(s);
    for (const i of this.items)
      P1(n, s, i);
    return s;
  }
  toString(t, n, r) {
    if (!t)
      return JSON.stringify(this);
    for (const s of this.items)
      if (!Ae(s))
        throw new Error(`Map items must all be pairs; found ${JSON.stringify(s)} instead`);
    return !t.allNullValues && this.hasAllNullValues(!1) && (t = Object.assign({}, t, { allNullValues: !0 })), I1(this, t, {
      blockItemPrefix: "",
      flowChars: { start: "{", end: "}" },
      itemIndent: t.indent || "",
      onChompKeep: r,
      onComment: n
    });
  }
}
const cs = {
  collection: "map",
  default: !0,
  nodeClass: xt,
  tag: "tag:yaml.org,2002:map",
  resolve(e, t) {
    return Ve(e) || t("Expected a mapping for this tag"), e;
  },
  createNode: (e, t, n) => xt.from(e, t, n)
};
class ar extends _1 {
  static get tagName() {
    return "tag:yaml.org,2002:seq";
  }
  constructor(t) {
    super(ls, t), this.items = [];
  }
  add(t) {
    this.items.push(t);
  }
  /**
   * Removes a value from the collection.
   *
   * `key` must contain a representation of an integer for this to succeed.
   * It may be wrapped in a `Scalar`.
   *
   * @returns `true` if the item was found and removed.
   */
  delete(t) {
    const n = di(t);
    return typeof n != "number" ? !1 : this.items.splice(n, 1).length > 0;
  }
  get(t, n) {
    const r = di(t);
    if (typeof r != "number")
      return;
    const s = this.items[r];
    return !n && ae(s) ? s.value : s;
  }
  /**
   * Checks if the collection includes a value with the key `key`.
   *
   * `key` must contain a representation of an integer for this to succeed.
   * It may be wrapped in a `Scalar`.
   */
  has(t) {
    const n = di(t);
    return typeof n == "number" && n < this.items.length;
  }
  /**
   * Sets a value in this collection. For `!!set`, `value` needs to be a
   * boolean to add/remove the item from the set.
   *
   * If `key` does not contain a representation of an integer, this will throw.
   * It may be wrapped in a `Scalar`.
   */
  set(t, n) {
    const r = di(t);
    if (typeof r != "number")
      throw new Error(`Expected a valid index, not ${t}.`);
    const s = this.items[r];
    ae(s) && F1(n) ? s.value = n : this.items[r] = n;
  }
  toJSON(t, n) {
    const r = [];
    n?.onCreate && n.onCreate(r);
    let s = 0;
    for (const i of this.items)
      r.push(kt(i, String(s++), n));
    return r;
  }
  toString(t, n, r) {
    return t ? I1(this, t, {
      blockItemPrefix: "- ",
      flowChars: { start: "[", end: "]" },
      itemIndent: (t.indent || "") + "  ",
      onChompKeep: r,
      onComment: n
    }) : JSON.stringify(this);
  }
  static from(t, n, r) {
    const { replacer: s } = r, i = new this(t);
    if (n && Symbol.iterator in Object(n)) {
      let a = 0;
      for (let o of n) {
        if (typeof s == "function") {
          const l = n instanceof Set ? o : String(a++);
          o = s.call(n, l, o);
        }
        i.items.push(Ks(o, void 0, r));
      }
    }
    return i;
  }
}
function di(e) {
  let t = ae(e) ? e.value : e;
  return t && typeof t == "string" && (t = Number(t)), typeof t == "number" && Number.isInteger(t) && t >= 0 ? t : null;
}
const fs = {
  collection: "seq",
  default: !0,
  nodeClass: ar,
  tag: "tag:yaml.org,2002:seq",
  resolve(e, t) {
    return Be(e) || t("Expected a sequence for this tag"), e;
  },
  createNode: (e, t, n) => ar.from(e, t, n)
}, ka = {
  identify: (e) => typeof e == "string",
  default: !0,
  tag: "tag:yaml.org,2002:str",
  resolve: (e) => e,
  stringify(e, t, n, r) {
    return t = Object.assign({ actualString: !0 }, t), cu(e, t, n, r);
  }
}, Ca = {
  identify: (e) => e == null,
  createNode: () => new oe(null),
  default: !0,
  tag: "tag:yaml.org,2002:null",
  test: /^(?:~|[Nn]ull|NULL)?$/,
  resolve: () => new oe(null),
  stringify: ({ source: e }, t) => typeof e == "string" && Ca.test.test(e) ? e : t.options.nullStr
}, hu = {
  identify: (e) => typeof e == "boolean",
  default: !0,
  tag: "tag:yaml.org,2002:bool",
  test: /^(?:[Tt]rue|TRUE|[Ff]alse|FALSE)$/,
  resolve: (e) => new oe(e[0] === "t" || e[0] === "T"),
  stringify({ source: e, value: t }, n) {
    if (e && hu.test.test(e)) {
      const r = e[0] === "t" || e[0] === "T";
      if (t === r)
        return e;
    }
    return t ? n.options.trueStr : n.options.falseStr;
  }
};
function Bt({ format: e, minFractionDigits: t, tag: n, value: r }) {
  if (typeof r == "bigint")
    return String(r);
  const s = typeof r == "number" ? r : Number(r);
  if (!isFinite(s))
    return isNaN(s) ? ".nan" : s < 0 ? "-.inf" : ".inf";
  let i = JSON.stringify(r);
  if (!e && t && (!n || n === "tag:yaml.org,2002:float") && /^\d/.test(i)) {
    let a = i.indexOf(".");
    a < 0 && (a = i.length, i += ".");
    let o = t - (i.length - a - 1);
    for (; o-- > 0; )
      i += "0";
  }
  return i;
}
const $1 = {
  identify: (e) => typeof e == "number",
  default: !0,
  tag: "tag:yaml.org,2002:float",
  test: /^(?:[-+]?\.(?:inf|Inf|INF)|\.nan|\.NaN|\.NAN)$/,
  resolve: (e) => e.slice(-3).toLowerCase() === "nan" ? NaN : e[0] === "-" ? Number.NEGATIVE_INFINITY : Number.POSITIVE_INFINITY,
  stringify: Bt
}, B1 = {
  identify: (e) => typeof e == "number",
  default: !0,
  tag: "tag:yaml.org,2002:float",
  format: "EXP",
  test: /^[-+]?(?:\.[0-9]+|[0-9]+(?:\.[0-9]*)?)[eE][-+]?[0-9]+$/,
  resolve: (e) => parseFloat(e),
  stringify(e) {
    const t = Number(e.value);
    return isFinite(t) ? t.toExponential() : Bt(e);
  }
}, V1 = {
  identify: (e) => typeof e == "number",
  default: !0,
  tag: "tag:yaml.org,2002:float",
  test: /^[-+]?(?:\.[0-9]+|[0-9]+\.[0-9]*)$/,
  resolve(e) {
    const t = new oe(parseFloat(e)), n = e.indexOf(".");
    return n !== -1 && e[e.length - 1] === "0" && (t.minFractionDigits = e.length - n - 1), t;
  },
  stringify: Bt
}, Fa = (e) => typeof e == "bigint" || Number.isInteger(e), du = (e, t, n, { intAsBigInt: r }) => r ? BigInt(e) : parseInt(e.substring(t), n);
function j1(e, t, n) {
  const { value: r } = e;
  return Fa(r) && r >= 0 ? n + r.toString(t) : Bt(e);
}
const U1 = {
  identify: (e) => Fa(e) && e >= 0,
  default: !0,
  tag: "tag:yaml.org,2002:int",
  format: "OCT",
  test: /^0o[0-7]+$/,
  resolve: (e, t, n) => du(e, 2, 8, n),
  stringify: (e) => j1(e, 8, "0o")
}, q1 = {
  identify: Fa,
  default: !0,
  tag: "tag:yaml.org,2002:int",
  test: /^[-+]?[0-9]+$/,
  resolve: (e, t, n) => du(e, 0, 10, n),
  stringify: Bt
}, W1 = {
  identify: (e) => Fa(e) && e >= 0,
  default: !0,
  tag: "tag:yaml.org,2002:int",
  format: "HEX",
  test: /^0x[0-9a-fA-F]+$/,
  resolve: (e, t, n) => du(e, 2, 16, n),
  stringify: (e) => j1(e, 16, "0x")
}, Wb = [
  cs,
  fs,
  ka,
  Ca,
  hu,
  U1,
  q1,
  W1,
  $1,
  B1,
  V1
];
function Bh(e) {
  return typeof e == "bigint" || Number.isInteger(e);
}
const mi = ({ value: e }) => JSON.stringify(e), Hb = [
  {
    identify: (e) => typeof e == "string",
    default: !0,
    tag: "tag:yaml.org,2002:str",
    resolve: (e) => e,
    stringify: mi
  },
  {
    identify: (e) => e == null,
    createNode: () => new oe(null),
    default: !0,
    tag: "tag:yaml.org,2002:null",
    test: /^null$/,
    resolve: () => null,
    stringify: mi
  },
  {
    identify: (e) => typeof e == "boolean",
    default: !0,
    tag: "tag:yaml.org,2002:bool",
    test: /^true$|^false$/,
    resolve: (e) => e === "true",
    stringify: mi
  },
  {
    identify: Bh,
    default: !0,
    tag: "tag:yaml.org,2002:int",
    test: /^-?(?:0|[1-9][0-9]*)$/,
    resolve: (e, t, { intAsBigInt: n }) => n ? BigInt(e) : parseInt(e, 10),
    stringify: ({ value: e }) => Bh(e) ? e.toString() : JSON.stringify(e)
  },
  {
    identify: (e) => typeof e == "number",
    default: !0,
    tag: "tag:yaml.org,2002:float",
    test: /^-?(?:0|[1-9][0-9]*)(?:\.[0-9]*)?(?:[eE][-+]?[0-9]+)?$/,
    resolve: (e) => parseFloat(e),
    stringify: mi
  }
], Yb = {
  default: !0,
  tag: "",
  test: /^/,
  resolve(e, t) {
    return t(`Unresolved plain scalar ${JSON.stringify(e)}`), e;
  }
}, zb = [cs, fs].concat(Hb, Yb), mu = {
  identify: (e) => e instanceof Uint8Array,
  // Buffer inherits from Uint8Array
  default: !1,
  tag: "tag:yaml.org,2002:binary",
  /**
   * Returns a Buffer in node and an Uint8Array in browsers
   *
   * To use the resulting buffer as an image, you'll want to do something like:
   *
   *   const blob = new Blob([buffer], { type: 'image/jpeg' })
   *   document.querySelector('#photo').src = URL.createObjectURL(blob)
   */
  resolve(e, t) {
    if (typeof atob == "function") {
      const n = atob(e.replace(/[\n\r]/g, "")), r = new Uint8Array(n.length);
      for (let s = 0; s < n.length; ++s)
        r[s] = n.charCodeAt(s);
      return r;
    } else
      return t("This environment does not support reading binary tags; either Buffer or atob is required"), e;
  },
  stringify({ comment: e, type: t, value: n }, r, s, i) {
    if (!n)
      return "";
    const a = n;
    let o;
    if (typeof btoa == "function") {
      let l = "";
      for (let u = 0; u < a.length; ++u)
        l += String.fromCharCode(a[u]);
      o = btoa(l);
    } else
      throw new Error("This environment does not support writing binary tags; either Buffer or btoa is required");
    if (t ?? (t = oe.BLOCK_LITERAL), t !== oe.QUOTE_DOUBLE) {
      const l = Math.max(r.options.lineWidth - r.indent.length, r.options.minContentWidth), u = Math.ceil(o.length / l), f = new Array(u);
      for (let c = 0, d = 0; c < u; ++c, d += l)
        f[c] = o.substr(d, l);
      o = f.join(t === oe.BLOCK_LITERAL ? `
` : " ");
    }
    return cu({ comment: e, type: t, value: o }, r, s, i);
  }
};
function H1(e, t) {
  if (Be(e))
    for (let n = 0; n < e.items.length; ++n) {
      let r = e.items[n];
      if (!Ae(r)) {
        if (Ve(r)) {
          r.items.length > 1 && t("Each pair must have its own sequence indicator");
          const s = r.items[0] || new tt(new oe(null));
          if (r.commentBefore && (s.key.commentBefore = s.key.commentBefore ? `${r.commentBefore}
${s.key.commentBefore}` : r.commentBefore), r.comment) {
            const i = s.value ?? s.key;
            i.comment = i.comment ? `${r.comment}
${i.comment}` : r.comment;
          }
          r = s;
        }
        e.items[n] = Ae(r) ? r : new tt(r);
      }
    }
  else
    t("Expected a sequence for this tag");
  return e;
}
function Y1(e, t, n) {
  const { replacer: r } = n, s = new ar(e);
  s.tag = "tag:yaml.org,2002:pairs";
  let i = 0;
  if (t && Symbol.iterator in Object(t))
    for (let a of t) {
      typeof r == "function" && (a = r.call(t, String(i++), a));
      let o, l;
      if (Array.isArray(a))
        if (a.length === 2)
          o = a[0], l = a[1];
        else
          throw new TypeError(`Expected [key, value] tuple: ${a}`);
      else if (a && a instanceof Object) {
        const u = Object.keys(a);
        if (u.length === 1)
          o = u[0], l = a[o];
        else
          throw new TypeError(`Expected tuple with one key, not ${u.length} keys`);
      } else
        o = a;
      s.items.push(fu(o, l, n));
    }
  return s;
}
const pu = {
  collection: "seq",
  default: !1,
  tag: "tag:yaml.org,2002:pairs",
  resolve: H1,
  createNode: Y1
};
class Yr extends ar {
  constructor() {
    super(), this.add = xt.prototype.add.bind(this), this.delete = xt.prototype.delete.bind(this), this.get = xt.prototype.get.bind(this), this.has = xt.prototype.has.bind(this), this.set = xt.prototype.set.bind(this), this.tag = Yr.tag;
  }
  /**
   * If `ctx` is given, the return type is actually `Map<unknown, unknown>`,
   * but TypeScript won't allow widening the signature of a child method.
   */
  toJSON(t, n) {
    if (!n)
      return super.toJSON(t);
    const r = /* @__PURE__ */ new Map();
    n?.onCreate && n.onCreate(r);
    for (const s of this.items) {
      let i, a;
      if (Ae(s) ? (i = kt(s.key, "", n), a = kt(s.value, i, n)) : i = kt(s, "", n), r.has(i))
        throw new Error("Ordered maps must not include duplicate keys");
      r.set(i, a);
    }
    return r;
  }
  static from(t, n, r) {
    const s = Y1(t, n, r), i = new this();
    return i.items = s.items, i;
  }
}
Yr.tag = "tag:yaml.org,2002:omap";
const gu = {
  collection: "seq",
  identify: (e) => e instanceof Map,
  nodeClass: Yr,
  default: !1,
  tag: "tag:yaml.org,2002:omap",
  resolve(e, t) {
    const n = H1(e, t), r = [];
    for (const { key: s } of n.items)
      ae(s) && (r.includes(s.value) ? t(`Ordered maps must not include duplicate keys: ${s.value}`) : r.push(s.value));
    return Object.assign(new Yr(), n);
  },
  createNode: (e, t, n) => Yr.from(e, t, n)
};
function z1({ value: e, source: t }, n) {
  return t && (e ? G1 : J1).test.test(t) ? t : e ? n.options.trueStr : n.options.falseStr;
}
const G1 = {
  identify: (e) => e === !0,
  default: !0,
  tag: "tag:yaml.org,2002:bool",
  test: /^(?:Y|y|[Yy]es|YES|[Tt]rue|TRUE|[Oo]n|ON)$/,
  resolve: () => new oe(!0),
  stringify: z1
}, J1 = {
  identify: (e) => e === !1,
  default: !0,
  tag: "tag:yaml.org,2002:bool",
  test: /^(?:N|n|[Nn]o|NO|[Ff]alse|FALSE|[Oo]ff|OFF)$/,
  resolve: () => new oe(!1),
  stringify: z1
}, Gb = {
  identify: (e) => typeof e == "number",
  default: !0,
  tag: "tag:yaml.org,2002:float",
  test: /^(?:[-+]?\.(?:inf|Inf|INF)|\.nan|\.NaN|\.NAN)$/,
  resolve: (e) => e.slice(-3).toLowerCase() === "nan" ? NaN : e[0] === "-" ? Number.NEGATIVE_INFINITY : Number.POSITIVE_INFINITY,
  stringify: Bt
}, Jb = {
  identify: (e) => typeof e == "number",
  default: !0,
  tag: "tag:yaml.org,2002:float",
  format: "EXP",
  test: /^[-+]?(?:[0-9][0-9_]*)?(?:\.[0-9_]*)?[eE][-+]?[0-9]+$/,
  resolve: (e) => parseFloat(e.replace(/_/g, "")),
  stringify(e) {
    const t = Number(e.value);
    return isFinite(t) ? t.toExponential() : Bt(e);
  }
}, Qb = {
  identify: (e) => typeof e == "number",
  default: !0,
  tag: "tag:yaml.org,2002:float",
  test: /^[-+]?(?:[0-9][0-9_]*)?\.[0-9_]*$/,
  resolve(e) {
    const t = new oe(parseFloat(e.replace(/_/g, ""))), n = e.indexOf(".");
    if (n !== -1) {
      const r = e.substring(n + 1).replace(/_/g, "");
      r[r.length - 1] === "0" && (t.minFractionDigits = r.length);
    }
    return t;
  },
  stringify: Bt
}, ei = (e) => typeof e == "bigint" || Number.isInteger(e);
function _a(e, t, n, { intAsBigInt: r }) {
  const s = e[0];
  if ((s === "-" || s === "+") && (t += 1), e = e.substring(t).replace(/_/g, ""), r) {
    switch (n) {
      case 2:
        e = `0b${e}`;
        break;
      case 8:
        e = `0o${e}`;
        break;
      case 16:
        e = `0x${e}`;
        break;
    }
    const a = BigInt(e);
    return s === "-" ? BigInt(-1) * a : a;
  }
  const i = parseInt(e, n);
  return s === "-" ? -1 * i : i;
}
function yu(e, t, n) {
  const { value: r } = e;
  if (ei(r)) {
    const s = r.toString(t);
    return r < 0 ? "-" + n + s.substr(1) : n + s;
  }
  return Bt(e);
}
const Kb = {
  identify: ei,
  default: !0,
  tag: "tag:yaml.org,2002:int",
  format: "BIN",
  test: /^[-+]?0b[0-1_]+$/,
  resolve: (e, t, n) => _a(e, 2, 2, n),
  stringify: (e) => yu(e, 2, "0b")
}, Xb = {
  identify: ei,
  default: !0,
  tag: "tag:yaml.org,2002:int",
  format: "OCT",
  test: /^[-+]?0[0-7_]+$/,
  resolve: (e, t, n) => _a(e, 1, 8, n),
  stringify: (e) => yu(e, 8, "0")
}, Zb = {
  identify: ei,
  default: !0,
  tag: "tag:yaml.org,2002:int",
  test: /^[-+]?[0-9][0-9_]*$/,
  resolve: (e, t, n) => _a(e, 0, 10, n),
  stringify: Bt
}, e2 = {
  identify: ei,
  default: !0,
  tag: "tag:yaml.org,2002:int",
  format: "HEX",
  test: /^[-+]?0x[0-9a-fA-F_]+$/,
  resolve: (e, t, n) => _a(e, 2, 16, n),
  stringify: (e) => yu(e, 16, "0x")
};
class zr extends xt {
  constructor(t) {
    super(t), this.tag = zr.tag;
  }
  add(t) {
    let n;
    Ae(t) ? n = t : t && typeof t == "object" && "key" in t && "value" in t && t.value === null ? n = new tt(t.key, null) : n = new tt(t, null), Xn(this.items, n.key) || this.items.push(n);
  }
  /**
   * If `keepPair` is `true`, returns the Pair matching `key`.
   * Otherwise, returns the value of that Pair's key.
   */
  get(t, n) {
    const r = Xn(this.items, t);
    return !n && Ae(r) ? ae(r.key) ? r.key.value : r.key : r;
  }
  set(t, n) {
    if (typeof n != "boolean")
      throw new Error(`Expected boolean value for set(key, value) in a YAML set, not ${typeof n}`);
    const r = Xn(this.items, t);
    r && !n ? this.items.splice(this.items.indexOf(r), 1) : !r && n && this.items.push(new tt(t));
  }
  toJSON(t, n) {
    return super.toJSON(t, n, Set);
  }
  toString(t, n, r) {
    if (!t)
      return JSON.stringify(this);
    if (this.hasAllNullValues(!0))
      return super.toString(Object.assign({}, t, { allNullValues: !0 }), n, r);
    throw new Error("Set items must all have null values");
  }
  static from(t, n, r) {
    const { replacer: s } = r, i = new this(t);
    if (n && Symbol.iterator in Object(n))
      for (let a of n)
        typeof s == "function" && (a = s.call(n, a, a)), i.items.push(fu(a, null, r));
    return i;
  }
}
zr.tag = "tag:yaml.org,2002:set";
const bu = {
  collection: "map",
  identify: (e) => e instanceof Set,
  nodeClass: zr,
  default: !1,
  tag: "tag:yaml.org,2002:set",
  createNode: (e, t, n) => zr.from(e, t, n),
  resolve(e, t) {
    if (Ve(e)) {
      if (e.hasAllNullValues(!0))
        return Object.assign(new zr(), e);
      t("Set items must all have null values");
    } else
      t("Expected a mapping for this tag");
    return e;
  }
};
function vu(e, t) {
  const n = e[0], r = n === "-" || n === "+" ? e.substring(1) : e, s = (a) => t ? BigInt(a) : Number(a), i = r.replace(/_/g, "").split(":").reduce((a, o) => a * s(60) + s(o), s(0));
  return n === "-" ? s(-1) * i : i;
}
function Q1(e) {
  let { value: t } = e, n = (a) => a;
  if (typeof t == "bigint")
    n = (a) => BigInt(a);
  else if (isNaN(t) || !isFinite(t))
    return Bt(e);
  let r = "";
  t < 0 && (r = "-", t *= n(-1));
  const s = n(60), i = [t % s];
  return t < 60 ? i.unshift(0) : (t = (t - i[0]) / s, i.unshift(t % s), t >= 60 && (t = (t - i[0]) / s, i.unshift(t))), r + i.map((a) => String(a).padStart(2, "0")).join(":").replace(/000000\d*$/, "");
}
const K1 = {
  identify: (e) => typeof e == "bigint" || Number.isInteger(e),
  default: !0,
  tag: "tag:yaml.org,2002:int",
  format: "TIME",
  test: /^[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+$/,
  resolve: (e, t, { intAsBigInt: n }) => vu(e, n),
  stringify: Q1
}, X1 = {
  identify: (e) => typeof e == "number",
  default: !0,
  tag: "tag:yaml.org,2002:float",
  format: "TIME",
  test: /^[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+\.[0-9_]*$/,
  resolve: (e) => vu(e, !1),
  stringify: Q1
}, Ta = {
  identify: (e) => e instanceof Date,
  default: !0,
  tag: "tag:yaml.org,2002:timestamp",
  // If the time zone is omitted, the timestamp is assumed to be specified in UTC. The time part
  // may be omitted altogether, resulting in a date format. In such a case, the time part is
  // assumed to be 00:00:00Z (start of day, UTC).
  test: RegExp("^([0-9]{4})-([0-9]{1,2})-([0-9]{1,2})(?:(?:t|T|[ \\t]+)([0-9]{1,2}):([0-9]{1,2}):([0-9]{1,2}(\\.[0-9]+)?)(?:[ \\t]*(Z|[-+][012]?[0-9](?::[0-9]{2})?))?)?$"),
  resolve(e) {
    const t = e.match(Ta.test);
    if (!t)
      throw new Error("!!timestamp expects a date, starting with yyyy-mm-dd");
    const [, n, r, s, i, a, o] = t.map(Number), l = t[7] ? Number((t[7] + "00").substr(1, 3)) : 0;
    let u = Date.UTC(n, r - 1, s, i || 0, a || 0, o || 0, l);
    const f = t[8];
    if (f && f !== "Z") {
      let c = vu(f, !1);
      Math.abs(c) < 30 && (c *= 60), u -= 6e4 * c;
    }
    return new Date(u);
  },
  stringify: ({ value: e }) => e?.toISOString().replace(/(T00:00:00)?\.000Z$/, "") ?? ""
}, Vh = [
  cs,
  fs,
  ka,
  Ca,
  G1,
  J1,
  Kb,
  Xb,
  Zb,
  e2,
  Gb,
  Jb,
  Qb,
  mu,
  dn,
  gu,
  pu,
  bu,
  K1,
  X1,
  Ta
], jh = /* @__PURE__ */ new Map([
  ["core", Wb],
  ["failsafe", [cs, fs, ka]],
  ["json", zb],
  ["yaml11", Vh],
  ["yaml-1.1", Vh]
]), Uh = {
  binary: mu,
  bool: hu,
  float: V1,
  floatExp: B1,
  floatNaN: $1,
  floatTime: X1,
  int: q1,
  intHex: W1,
  intOct: U1,
  intTime: K1,
  map: cs,
  merge: dn,
  null: Ca,
  omap: gu,
  pairs: pu,
  seq: fs,
  set: bu,
  timestamp: Ta
}, t2 = {
  "tag:yaml.org,2002:binary": mu,
  "tag:yaml.org,2002:merge": dn,
  "tag:yaml.org,2002:omap": gu,
  "tag:yaml.org,2002:pairs": pu,
  "tag:yaml.org,2002:set": bu,
  "tag:yaml.org,2002:timestamp": Ta
};
function to(e, t, n) {
  const r = jh.get(t);
  if (r && !e)
    return n && !r.includes(dn) ? r.concat(dn) : r.slice();
  let s = r;
  if (!s)
    if (Array.isArray(e))
      s = [];
    else {
      const i = Array.from(jh.keys()).filter((a) => a !== "yaml11").map((a) => JSON.stringify(a)).join(", ");
      throw new Error(`Unknown schema "${t}"; use one of ${i} or define customTags array`);
    }
  if (Array.isArray(e))
    for (const i of e)
      s = s.concat(i);
  else typeof e == "function" && (s = e(s.slice()));
  return n && (s = s.concat(dn)), s.reduce((i, a) => {
    const o = typeof a == "string" ? Uh[a] : a;
    if (!o) {
      const l = JSON.stringify(a), u = Object.keys(Uh).map((f) => JSON.stringify(f)).join(", ");
      throw new Error(`Unknown custom tag ${l}; use one of ${u}`);
    }
    return i.includes(o) || i.push(o), i;
  }, []);
}
const n2 = (e, t) => e.key < t.key ? -1 : e.key > t.key ? 1 : 0;
class wu {
  constructor({ compat: t, customTags: n, merge: r, resolveKnownTags: s, schema: i, sortMapEntries: a, toStringDefaults: o }) {
    this.compat = Array.isArray(t) ? to(t, "compat") : t ? to(null, t) : null, this.name = typeof i == "string" && i || "core", this.knownTags = s ? t2 : {}, this.tags = to(n, this.name, r), this.toStringOptions = o ?? null, Object.defineProperty(this, Mn, { value: cs }), Object.defineProperty(this, Qt, { value: ka }), Object.defineProperty(this, ls, { value: fs }), this.sortMapEntries = typeof a == "function" ? a : a === !0 ? n2 : null;
  }
  clone() {
    const t = Object.create(wu.prototype, Object.getOwnPropertyDescriptors(this));
    return t.tags = this.tags.slice(), t;
  }
}
function r2(e, t) {
  const n = [];
  let r = t.directives === !0;
  if (t.directives !== !1 && e.directives) {
    const l = e.directives.toString(e);
    l ? (n.push(l), r = !0) : e.directives.docStart && (r = !0);
  }
  r && n.push("---");
  const s = M1(e, t), { commentString: i } = s.options;
  if (e.commentBefore) {
    n.length !== 1 && n.unshift("");
    const l = i(e.commentBefore);
    n.unshift(un(l, ""));
  }
  let a = !1, o = null;
  if (e.contents) {
    if (De(e.contents)) {
      if (e.contents.spaceBefore && r && n.push(""), e.contents.commentBefore) {
        const f = i(e.contents.commentBefore);
        n.push(un(f, ""));
      }
      s.forceBlockIndent = !!e.comment, o = e.contents.comment;
    }
    const l = o ? void 0 : () => a = !0;
    let u = rs(e.contents, s, () => o = null, l);
    o && (u += Kn(u, "", i(o))), (u[0] === "|" || u[0] === ">") && n[n.length - 1] === "---" ? n[n.length - 1] = `--- ${u}` : n.push(u);
  } else
    n.push(rs(e.contents, s));
  if (e.directives?.docEnd)
    if (e.comment) {
      const l = i(e.comment);
      l.includes(`
`) ? (n.push("..."), n.push(un(l, ""))) : n.push(`... ${l}`);
    } else
      n.push("...");
  else {
    let l = e.comment;
    l && a && (l = l.replace(/^\n+/, "")), l && ((!a || o) && n[n.length - 1] !== "" && n.push(""), n.push(un(i(l), "")));
  }
  return n.join(`
`) + `
`;
}
class ti {
  constructor(t, n, r) {
    this.commentBefore = null, this.comment = null, this.errors = [], this.warnings = [], Object.defineProperty(this, Ct, { value: Dl });
    let s = null;
    typeof n == "function" || Array.isArray(n) ? s = n : r === void 0 && n && (r = n, n = void 0);
    const i = Object.assign({
      intAsBigInt: !1,
      keepSourceTokens: !1,
      logLevel: "warn",
      prettyErrors: !0,
      strict: !0,
      stringKeys: !1,
      uniqueKeys: !0,
      version: "1.2"
    }, r);
    this.options = i;
    let { version: a } = i;
    r?._directives ? (this.directives = r._directives.atDocument(), this.directives.yaml.explicit && (a = this.directives.yaml.version)) : this.directives = new Ze({ version: a }), this.setSchema(a, r), this.contents = t === void 0 ? null : this.createNode(t, s, r);
  }
  /**
   * Create a deep copy of this Document and its contents.
   *
   * Custom Node values that inherit from `Object` still refer to their original instances.
   */
  clone() {
    const t = Object.create(ti.prototype, {
      [Ct]: { value: Dl }
    });
    return t.commentBefore = this.commentBefore, t.comment = this.comment, t.errors = this.errors.slice(), t.warnings = this.warnings.slice(), t.options = Object.assign({}, this.options), this.directives && (t.directives = this.directives.clone()), t.schema = this.schema.clone(), t.contents = De(this.contents) ? this.contents.clone(t.schema) : this.contents, this.range && (t.range = this.range.slice()), t;
  }
  /** Adds a value to the document. */
  add(t) {
    Lr(this.contents) && this.contents.add(t);
  }
  /** Adds a value to the document. */
  addIn(t, n) {
    Lr(this.contents) && this.contents.addIn(t, n);
  }
  /**
   * Create a new `Alias` node, ensuring that the target `node` has the required anchor.
   *
   * If `node` already has an anchor, `name` is ignored.
   * Otherwise, the `node.anchor` value will be set to `name`,
   * or if an anchor with that name is already present in the document,
   * `name` will be used as a prefix for a new unique anchor.
   * If `name` is undefined, the generated anchor will use 'a' as a prefix.
   */
  createAlias(t, n) {
    if (!t.anchor) {
      const r = k1(this);
      t.anchor = // eslint-disable-next-line @typescript-eslint/prefer-nullish-coalescing
      !n || r.has(n) ? C1(n || "a", r) : n;
    }
    return new uu(t.anchor);
  }
  createNode(t, n, r) {
    let s;
    if (typeof n == "function")
      t = n.call({ "": t }, "", t), s = n;
    else if (Array.isArray(n)) {
      const x = (k) => typeof k == "number" || k instanceof String || k instanceof Number, N = n.filter(x).map(String);
      N.length > 0 && (n = n.concat(N)), s = n;
    } else r === void 0 && n && (r = n, n = void 0);
    const { aliasDuplicateObjects: i, anchorPrefix: a, flow: o, keepUndefined: l, onTagObj: u, tag: f } = r ?? {}, { onAnchor: c, setAnchors: d, sourceObjects: v } = _b(
      this,
      // eslint-disable-next-line @typescript-eslint/prefer-nullish-coalescing
      a || "a"
    ), D = {
      aliasDuplicateObjects: i ?? !0,
      keepUndefined: l ?? !1,
      onAnchor: c,
      onTagObj: u,
      replacer: s,
      schema: this.schema,
      sourceObjects: v
    }, S = Ks(t, f, D);
    return o && Pe(S) && (S.flow = !0), d(), S;
  }
  /**
   * Convert a key and a value into a `Pair` using the current schema,
   * recursively wrapping all values as `Scalar` or `Collection` nodes.
   */
  createPair(t, n, r = {}) {
    const s = this.createNode(t, null, r), i = this.createNode(n, null, r);
    return new tt(s, i);
  }
  /**
   * Removes a value from the document.
   * @returns `true` if the item was found and removed.
   */
  delete(t) {
    return Lr(this.contents) ? this.contents.delete(t) : !1;
  }
  /**
   * Removes a value from the document.
   * @returns `true` if the item was found and removed.
   */
  deleteIn(t) {
    return Ls(t) ? this.contents == null ? !1 : (this.contents = null, !0) : Lr(this.contents) ? this.contents.deleteIn(t) : !1;
  }
  /**
   * Returns item at `key`, or `undefined` if not found. By default unwraps
   * scalar values from their surrounding node; to disable set `keepScalar` to
   * `true` (collections are always returned intact).
   */
  get(t, n) {
    return Pe(this.contents) ? this.contents.get(t, n) : void 0;
  }
  /**
   * Returns item at `path`, or `undefined` if not found. By default unwraps
   * scalar values from their surrounding node; to disable set `keepScalar` to
   * `true` (collections are always returned intact).
   */
  getIn(t, n) {
    return Ls(t) ? !n && ae(this.contents) ? this.contents.value : this.contents : Pe(this.contents) ? this.contents.getIn(t, n) : void 0;
  }
  /**
   * Checks if the document includes a value with the key `key`.
   */
  has(t) {
    return Pe(this.contents) ? this.contents.has(t) : !1;
  }
  /**
   * Checks if the document includes a value at `path`.
   */
  hasIn(t) {
    return Ls(t) ? this.contents !== void 0 : Pe(this.contents) ? this.contents.hasIn(t) : !1;
  }
  /**
   * Sets a value in this document. For `!!set`, `value` needs to be a
   * boolean to add/remove the item from the set.
   */
  set(t, n) {
    this.contents == null ? this.contents = aa(this.schema, [t], n) : Lr(this.contents) && this.contents.set(t, n);
  }
  /**
   * Sets a value in this document. For `!!set`, `value` needs to be a
   * boolean to add/remove the item from the set.
   */
  setIn(t, n) {
    Ls(t) ? this.contents = n : this.contents == null ? this.contents = aa(this.schema, Array.from(t), n) : Lr(this.contents) && this.contents.setIn(t, n);
  }
  /**
   * Change the YAML version and schema used by the document.
   * A `null` version disables support for directives, explicit tags, anchors, and aliases.
   * It also requires the `schema` option to be given as a `Schema` instance value.
   *
   * Overrides all previously set schema options.
   */
  setSchema(t, n = {}) {
    typeof t == "number" && (t = String(t));
    let r;
    switch (t) {
      case "1.1":
        this.directives ? this.directives.yaml.version = "1.1" : this.directives = new Ze({ version: "1.1" }), r = { resolveKnownTags: !1, schema: "yaml-1.1" };
        break;
      case "1.2":
      case "next":
        this.directives ? this.directives.yaml.version = t : this.directives = new Ze({ version: t }), r = { resolveKnownTags: !0, schema: "core" };
        break;
      case null:
        this.directives && delete this.directives, r = null;
        break;
      default: {
        const s = JSON.stringify(t);
        throw new Error(`Expected '1.1', '1.2' or null as first argument, but found: ${s}`);
      }
    }
    if (n.schema instanceof Object)
      this.schema = n.schema;
    else if (r)
      this.schema = new wu(Object.assign(r, n));
    else
      throw new Error("With a null YAML version, the { schema: Schema } option is required");
  }
  // json & jsonArg are only used from toJSON()
  toJS({ json: t, jsonArg: n, mapAsMap: r, maxAliasCount: s, onAnchor: i, reviver: a } = {}) {
    const o = {
      anchors: /* @__PURE__ */ new Map(),
      doc: this,
      keep: !t,
      mapAsMap: r === !0,
      mapKeyWarned: !1,
      maxAliasCount: typeof s == "number" ? s : 100
    }, l = kt(this.contents, n ?? "", o);
    if (typeof i == "function")
      for (const { count: u, res: f } of o.anchors.values())
        i(f, u);
    return typeof a == "function" ? Tr(a, { "": l }, "", l) : l;
  }
  /**
   * A JSON representation of the document `contents`.
   *
   * @param jsonArg Used by `JSON.stringify` to indicate the array index or
   *   property name.
   */
  toJSON(t, n) {
    return this.toJS({ json: !0, jsonArg: t, mapAsMap: !1, onAnchor: n });
  }
  /** A YAML representation of the document. */
  toString(t = {}) {
    if (this.errors.length > 0)
      throw new Error("Document with errors cannot be stringified");
    if ("indent" in t && (!Number.isInteger(t.indent) || Number(t.indent) <= 0)) {
      const n = JSON.stringify(t.indent);
      throw new Error(`"indent" option must be a positive integer, not ${n}`);
    }
    return r2(this, t);
  }
}
function Lr(e) {
  if (Pe(e))
    return !0;
  throw new Error("Expected a YAML collection as document contents");
}
class Z1 extends Error {
  constructor(t, n, r, s) {
    super(), this.name = t, this.code = r, this.message = s, this.pos = n;
  }
}
class ks extends Z1 {
  constructor(t, n, r) {
    super("YAMLParseError", t, n, r);
  }
}
class s2 extends Z1 {
  constructor(t, n, r) {
    super("YAMLWarning", t, n, r);
  }
}
const qh = (e, t) => (n) => {
  if (n.pos[0] === -1)
    return;
  n.linePos = n.pos.map((o) => t.linePos(o));
  const { line: r, col: s } = n.linePos[0];
  n.message += ` at line ${r}, column ${s}`;
  let i = s - 1, a = e.substring(t.lineStarts[r - 1], t.lineStarts[r]).replace(/[\n\r]+$/, "");
  if (i >= 60 && a.length > 80) {
    const o = Math.min(i - 39, a.length - 79);
    a = "…" + a.substring(o), i -= o - 1;
  }
  if (a.length > 80 && (a = a.substring(0, 79) + "…"), r > 1 && /^ *$/.test(a.substring(0, i))) {
    let o = e.substring(t.lineStarts[r - 2], t.lineStarts[r - 1]);
    o.length > 80 && (o = o.substring(0, 79) + `…
`), a = o + a;
  }
  if (/[^ ]/.test(a)) {
    let o = 1;
    const l = n.linePos[1];
    l && l.line === r && l.col > s && (o = Math.max(1, Math.min(l.col - s, 80 - i)));
    const u = " ".repeat(i) + "^".repeat(o);
    n.message += `:

${a}
${u}
`;
  }
};
function ss(e, { flow: t, indicator: n, next: r, offset: s, onError: i, parentIndent: a, startOnNewline: o }) {
  let l = !1, u = o, f = o, c = "", d = "", v = !1, D = !1, S = null, x = null, N = null, k = null, y = null, b = null, h = null;
  for (const E of e)
    switch (D && (E.type !== "space" && E.type !== "newline" && E.type !== "comma" && i(E.offset, "MISSING_CHAR", "Tags and anchors must be separated from the next token by white space"), D = !1), S && (u && E.type !== "comment" && E.type !== "newline" && i(S, "TAB_AS_INDENT", "Tabs are not allowed as indentation"), S = null), E.type) {
      case "space":
        !t && (n !== "doc-start" || r?.type !== "flow-collection") && E.source.includes("	") && (S = E), f = !0;
        break;
      case "comment": {
        f || i(E, "MISSING_CHAR", "Comments must be separated from other tokens by white space characters");
        const w = E.source.substring(1) || " ";
        c ? c += d + w : c = w, d = "", u = !1;
        break;
      }
      case "newline":
        u ? c ? c += E.source : (!b || n !== "seq-item-ind") && (l = !0) : d += E.source, u = !0, v = !0, (x || N) && (k = E), f = !0;
        break;
      case "anchor":
        x && i(E, "MULTIPLE_ANCHORS", "A node can have at most one anchor"), E.source.endsWith(":") && i(E.offset + E.source.length - 1, "BAD_ALIAS", "Anchor ending in : is ambiguous", !0), x = E, h ?? (h = E.offset), u = !1, f = !1, D = !0;
        break;
      case "tag": {
        N && i(E, "MULTIPLE_TAGS", "A node can have at most one tag"), N = E, h ?? (h = E.offset), u = !1, f = !1, D = !0;
        break;
      }
      case n:
        (x || N) && i(E, "BAD_PROP_ORDER", `Anchors and tags must be after the ${E.source} indicator`), b && i(E, "UNEXPECTED_TOKEN", `Unexpected ${E.source} in ${t ?? "collection"}`), b = E, u = n === "seq-item-ind" || n === "explicit-key-ind", f = !1;
        break;
      case "comma":
        if (t) {
          y && i(E, "UNEXPECTED_TOKEN", `Unexpected , in ${t}`), y = E, u = !1, f = !1;
          break;
        }
      // else fallthrough
      default:
        i(E, "UNEXPECTED_TOKEN", `Unexpected ${E.type} token`), u = !1, f = !1;
    }
  const m = e[e.length - 1], p = m ? m.offset + m.source.length : s;
  return D && r && r.type !== "space" && r.type !== "newline" && r.type !== "comma" && (r.type !== "scalar" || r.source !== "") && i(r.offset, "MISSING_CHAR", "Tags and anchors must be separated from the next token by white space"), S && (u && S.indent <= a || r?.type === "block-map" || r?.type === "block-seq") && i(S, "TAB_AS_INDENT", "Tabs are not allowed as indentation"), {
    comma: y,
    found: b,
    spaceBefore: l,
    comment: c,
    hasNewline: v,
    anchor: x,
    tag: N,
    newlineAfterProp: k,
    end: p,
    start: h ?? p
  };
}
function Xs(e) {
  if (!e)
    return null;
  switch (e.type) {
    case "alias":
    case "scalar":
    case "double-quoted-scalar":
    case "single-quoted-scalar":
      if (e.source.includes(`
`))
        return !0;
      if (e.end) {
        for (const t of e.end)
          if (t.type === "newline")
            return !0;
      }
      return !1;
    case "flow-collection":
      for (const t of e.items) {
        for (const n of t.start)
          if (n.type === "newline")
            return !0;
        if (t.sep) {
          for (const n of t.sep)
            if (n.type === "newline")
              return !0;
        }
        if (Xs(t.key) || Xs(t.value))
          return !0;
      }
      return !1;
    default:
      return !0;
  }
}
function xl(e, t, n) {
  if (t?.type === "flow-collection") {
    const r = t.end[0];
    r.indent === e && (r.source === "]" || r.source === "}") && Xs(t) && n(r, "BAD_INDENT", "Flow end indicator should be more indented than parent", !0);
  }
}
function em(e, t, n) {
  const { uniqueKeys: r } = e.options;
  if (r === !1)
    return !1;
  const s = typeof r == "function" ? r : (i, a) => i === a || ae(i) && ae(a) && i.value === a.value;
  return t.some((i) => s(i.key, n));
}
const Wh = "All mapping items must start at the same column";
function i2({ composeNode: e, composeEmptyNode: t }, n, r, s, i) {
  const a = i?.nodeClass ?? xt, o = new a(n.schema);
  n.atRoot && (n.atRoot = !1);
  let l = r.offset, u = null;
  for (const f of r.items) {
    const { start: c, key: d, sep: v, value: D } = f, S = ss(c, {
      indicator: "explicit-key-ind",
      next: d ?? v?.[0],
      offset: l,
      onError: s,
      parentIndent: r.indent,
      startOnNewline: !0
    }), x = !S.found;
    if (x) {
      if (d && (d.type === "block-seq" ? s(l, "BLOCK_AS_IMPLICIT_KEY", "A block sequence may not be used as an implicit map key") : "indent" in d && d.indent !== r.indent && s(l, "BAD_INDENT", Wh)), !S.anchor && !S.tag && !v) {
        u = S.end, S.comment && (o.comment ? o.comment += `
` + S.comment : o.comment = S.comment);
        continue;
      }
      (S.newlineAfterProp || Xs(d)) && s(d ?? c[c.length - 1], "MULTILINE_IMPLICIT_KEY", "Implicit keys need to be on a single line");
    } else S.found?.indent !== r.indent && s(l, "BAD_INDENT", Wh);
    n.atKey = !0;
    const N = S.end, k = d ? e(n, d, S, s) : t(n, N, c, null, S, s);
    n.schema.compat && xl(r.indent, d, s), n.atKey = !1, em(n, o.items, k) && s(N, "DUPLICATE_KEY", "Map keys must be unique");
    const y = ss(v ?? [], {
      indicator: "map-value-ind",
      next: D,
      offset: k.range[2],
      onError: s,
      parentIndent: r.indent,
      startOnNewline: !d || d.type === "block-scalar"
    });
    if (l = y.end, y.found) {
      x && (D?.type === "block-map" && !y.hasNewline && s(l, "BLOCK_AS_IMPLICIT_KEY", "Nested mappings are not allowed in compact mappings"), n.options.strict && S.start < y.found.offset - 1024 && s(k.range, "KEY_OVER_1024_CHARS", "The : indicator must be at most 1024 chars after the start of an implicit block mapping key"));
      const b = D ? e(n, D, y, s) : t(n, l, v, null, y, s);
      n.schema.compat && xl(r.indent, D, s), l = b.range[2];
      const h = new tt(k, b);
      n.options.keepSourceTokens && (h.srcToken = f), o.items.push(h);
    } else {
      x && s(k.range, "MISSING_CHAR", "Implicit map keys need to be followed by map values"), y.comment && (k.comment ? k.comment += `
` + y.comment : k.comment = y.comment);
      const b = new tt(k);
      n.options.keepSourceTokens && (b.srcToken = f), o.items.push(b);
    }
  }
  return u && u < l && s(u, "IMPOSSIBLE", "Map comment with trailing content"), o.range = [r.offset, l, u ?? l], o;
}
function a2({ composeNode: e, composeEmptyNode: t }, n, r, s, i) {
  const a = i?.nodeClass ?? ar, o = new a(n.schema);
  n.atRoot && (n.atRoot = !1), n.atKey && (n.atKey = !1);
  let l = r.offset, u = null;
  for (const { start: f, value: c } of r.items) {
    const d = ss(f, {
      indicator: "seq-item-ind",
      next: c,
      offset: l,
      onError: s,
      parentIndent: r.indent,
      startOnNewline: !0
    });
    if (!d.found)
      if (d.anchor || d.tag || c)
        c && c.type === "block-seq" ? s(d.end, "BAD_INDENT", "All sequence items must start at the same column") : s(l, "MISSING_CHAR", "Sequence item without - indicator");
      else {
        u = d.end, d.comment && (o.comment = d.comment);
        continue;
      }
    const v = c ? e(n, c, d, s) : t(n, d.end, f, null, d, s);
    n.schema.compat && xl(r.indent, c, s), l = v.range[2], o.items.push(v);
  }
  return o.range = [r.offset, l, u ?? l], o;
}
function ni(e, t, n, r) {
  let s = "";
  if (e) {
    let i = !1, a = "";
    for (const o of e) {
      const { source: l, type: u } = o;
      switch (u) {
        case "space":
          i = !0;
          break;
        case "comment": {
          n && !i && r(o, "MISSING_CHAR", "Comments must be separated from other tokens by white space characters");
          const f = l.substring(1) || " ";
          s ? s += a + f : s = f, a = "";
          break;
        }
        case "newline":
          s && (a += l), i = !0;
          break;
        default:
          r(o, "UNEXPECTED_TOKEN", `Unexpected ${u} at node end`);
      }
      t += l.length;
    }
  }
  return { comment: s, offset: t };
}
const no = "Block collections are not allowed within flow collections", ro = (e) => e && (e.type === "block-map" || e.type === "block-seq");
function o2({ composeNode: e, composeEmptyNode: t }, n, r, s, i) {
  const a = r.start.source === "{", o = a ? "flow map" : "flow sequence", l = i?.nodeClass ?? (a ? xt : ar), u = new l(n.schema);
  u.flow = !0;
  const f = n.atRoot;
  f && (n.atRoot = !1), n.atKey && (n.atKey = !1);
  let c = r.offset + r.start.source.length;
  for (let x = 0; x < r.items.length; ++x) {
    const N = r.items[x], { start: k, key: y, sep: b, value: h } = N, m = ss(k, {
      flow: o,
      indicator: "explicit-key-ind",
      next: y ?? b?.[0],
      offset: c,
      onError: s,
      parentIndent: r.indent,
      startOnNewline: !1
    });
    if (!m.found) {
      if (!m.anchor && !m.tag && !b && !h) {
        x === 0 && m.comma ? s(m.comma, "UNEXPECTED_TOKEN", `Unexpected , in ${o}`) : x < r.items.length - 1 && s(m.start, "UNEXPECTED_TOKEN", `Unexpected empty item in ${o}`), m.comment && (u.comment ? u.comment += `
` + m.comment : u.comment = m.comment), c = m.end;
        continue;
      }
      !a && n.options.strict && Xs(y) && s(
        y,
        // checked by containsNewline()
        "MULTILINE_IMPLICIT_KEY",
        "Implicit keys of flow sequence pairs need to be on a single line"
      );
    }
    if (x === 0)
      m.comma && s(m.comma, "UNEXPECTED_TOKEN", `Unexpected , in ${o}`);
    else if (m.comma || s(m.start, "MISSING_CHAR", `Missing , between ${o} items`), m.comment) {
      let p = "";
      e: for (const E of k)
        switch (E.type) {
          case "comma":
          case "space":
            break;
          case "comment":
            p = E.source.substring(1);
            break e;
          default:
            break e;
        }
      if (p) {
        let E = u.items[u.items.length - 1];
        Ae(E) && (E = E.value ?? E.key), E.comment ? E.comment += `
` + p : E.comment = p, m.comment = m.comment.substring(p.length + 1);
      }
    }
    if (!a && !b && !m.found) {
      const p = h ? e(n, h, m, s) : t(n, m.end, b, null, m, s);
      u.items.push(p), c = p.range[2], ro(h) && s(p.range, "BLOCK_IN_FLOW", no);
    } else {
      n.atKey = !0;
      const p = m.end, E = y ? e(n, y, m, s) : t(n, p, k, null, m, s);
      ro(y) && s(E.range, "BLOCK_IN_FLOW", no), n.atKey = !1;
      const w = ss(b ?? [], {
        flow: o,
        indicator: "map-value-ind",
        next: h,
        offset: E.range[2],
        onError: s,
        parentIndent: r.indent,
        startOnNewline: !1
      });
      if (w.found) {
        if (!a && !m.found && n.options.strict) {
          if (b)
            for (const A of b) {
              if (A === w.found)
                break;
              if (A.type === "newline") {
                s(A, "MULTILINE_IMPLICIT_KEY", "Implicit keys of flow sequence pairs need to be on a single line");
                break;
              }
            }
          m.start < w.found.offset - 1024 && s(w.found, "KEY_OVER_1024_CHARS", "The : indicator must be at most 1024 chars after the start of an implicit flow sequence key");
        }
      } else h && ("source" in h && h.source && h.source[0] === ":" ? s(h, "MISSING_CHAR", `Missing space after : in ${o}`) : s(w.start, "MISSING_CHAR", `Missing , or : between ${o} items`));
      const L = h ? e(n, h, w, s) : w.found ? t(n, w.end, b, null, w, s) : null;
      L ? ro(h) && s(L.range, "BLOCK_IN_FLOW", no) : w.comment && (E.comment ? E.comment += `
` + w.comment : E.comment = w.comment);
      const C = new tt(E, L);
      if (n.options.keepSourceTokens && (C.srcToken = N), a) {
        const A = u;
        em(n, A.items, E) && s(p, "DUPLICATE_KEY", "Map keys must be unique"), A.items.push(C);
      } else {
        const A = new xt(n.schema);
        A.flow = !0, A.items.push(C);
        const _ = (L ?? E).range;
        A.range = [E.range[0], _[1], _[2]], u.items.push(A);
      }
      c = L ? L.range[2] : w.end;
    }
  }
  const d = a ? "}" : "]", [v, ...D] = r.end;
  let S = c;
  if (v && v.source === d)
    S = v.offset + v.source.length;
  else {
    const x = o[0].toUpperCase() + o.substring(1), N = f ? `${x} must end with a ${d}` : `${x} in block collection must be sufficiently indented and end with a ${d}`;
    s(c, f ? "MISSING_CHAR" : "BAD_INDENT", N), v && v.source.length !== 1 && D.unshift(v);
  }
  if (D.length > 0) {
    const x = ni(D, S, n.options.strict, s);
    x.comment && (u.comment ? u.comment += `
` + x.comment : u.comment = x.comment), u.range = [r.offset, S, x.offset];
  } else
    u.range = [r.offset, S, S];
  return u;
}
function so(e, t, n, r, s, i) {
  const a = n.type === "block-map" ? i2(e, t, n, r, i) : n.type === "block-seq" ? a2(e, t, n, r, i) : o2(e, t, n, r, i), o = a.constructor;
  return s === "!" || s === o.tagName ? (a.tag = o.tagName, a) : (s && (a.tag = s), a);
}
function l2(e, t, n, r, s) {
  const i = r.tag, a = i ? t.directives.tagName(i.source, (d) => s(i, "TAG_RESOLVE_FAILED", d)) : null;
  if (n.type === "block-seq") {
    const { anchor: d, newlineAfterProp: v } = r, D = d && i ? d.offset > i.offset ? d : i : d ?? i;
    D && (!v || v.offset < D.offset) && s(D, "MISSING_CHAR", "Missing newline after block sequence props");
  }
  const o = n.type === "block-map" ? "map" : n.type === "block-seq" ? "seq" : n.start.source === "{" ? "map" : "seq";
  if (!i || !a || a === "!" || a === xt.tagName && o === "map" || a === ar.tagName && o === "seq")
    return so(e, t, n, s, a);
  let l = t.schema.tags.find((d) => d.tag === a && d.collection === o);
  if (!l) {
    const d = t.schema.knownTags[a];
    if (d && d.collection === o)
      t.schema.tags.push(Object.assign({}, d, { default: !1 })), l = d;
    else
      return d ? s(i, "BAD_COLLECTION_TYPE", `${d.tag} used for ${o} collection, but expects ${d.collection ?? "scalar"}`, !0) : s(i, "TAG_RESOLVE_FAILED", `Unresolved tag: ${a}`, !0), so(e, t, n, s, a);
  }
  const u = so(e, t, n, s, a, l), f = l.resolve?.(u, (d) => s(i, "TAG_RESOLVE_FAILED", d), t.options) ?? u, c = De(f) ? f : new oe(f);
  return c.range = u.range, c.tag = a, l?.format && (c.format = l.format), c;
}
function u2(e, t, n) {
  const r = t.offset, s = c2(t, e.options.strict, n);
  if (!s)
    return { value: "", type: null, comment: "", range: [r, r, r] };
  const i = s.mode === ">" ? oe.BLOCK_FOLDED : oe.BLOCK_LITERAL, a = t.source ? f2(t.source) : [];
  let o = a.length;
  for (let S = a.length - 1; S >= 0; --S) {
    const x = a[S][1];
    if (x === "" || x === "\r")
      o = S;
    else
      break;
  }
  if (o === 0) {
    const S = s.chomp === "+" && a.length > 0 ? `
`.repeat(Math.max(1, a.length - 1)) : "";
    let x = r + s.length;
    return t.source && (x += t.source.length), { value: S, type: i, comment: s.comment, range: [r, x, x] };
  }
  let l = t.indent + s.indent, u = t.offset + s.length, f = 0;
  for (let S = 0; S < o; ++S) {
    const [x, N] = a[S];
    if (N === "" || N === "\r")
      s.indent === 0 && x.length > l && (l = x.length);
    else {
      x.length < l && n(u + x.length, "MISSING_CHAR", "Block scalars with more-indented leading empty lines must use an explicit indentation indicator"), s.indent === 0 && (l = x.length), f = S, l === 0 && !e.atRoot && n(u, "BAD_INDENT", "Block scalar values in collections must be indented");
      break;
    }
    u += x.length + N.length + 1;
  }
  for (let S = a.length - 1; S >= o; --S)
    a[S][0].length > l && (o = S + 1);
  let c = "", d = "", v = !1;
  for (let S = 0; S < f; ++S)
    c += a[S][0].slice(l) + `
`;
  for (let S = f; S < o; ++S) {
    let [x, N] = a[S];
    u += x.length + N.length + 1;
    const k = N[N.length - 1] === "\r";
    if (k && (N = N.slice(0, -1)), N && x.length < l) {
      const b = `Block scalar lines must not be less indented than their ${s.indent ? "explicit indentation indicator" : "first line"}`;
      n(u - N.length - (k ? 2 : 1), "BAD_INDENT", b), x = "";
    }
    i === oe.BLOCK_LITERAL ? (c += d + x.slice(l) + N, d = `
`) : x.length > l || N[0] === "	" ? (d === " " ? d = `
` : !v && d === `
` && (d = `

`), c += d + x.slice(l) + N, d = `
`, v = !0) : N === "" ? d === `
` ? c += `
` : d = `
` : (c += d + N, d = " ", v = !1);
  }
  switch (s.chomp) {
    case "-":
      break;
    case "+":
      for (let S = o; S < a.length; ++S)
        c += `
` + a[S][0].slice(l);
      c[c.length - 1] !== `
` && (c += `
`);
      break;
    default:
      c += `
`;
  }
  const D = r + s.length + t.source.length;
  return { value: c, type: i, comment: s.comment, range: [r, D, D] };
}
function c2({ offset: e, props: t }, n, r) {
  if (t[0].type !== "block-scalar-header")
    return r(t[0], "IMPOSSIBLE", "Block scalar header not found"), null;
  const { source: s } = t[0], i = s[0];
  let a = 0, o = "", l = -1;
  for (let d = 1; d < s.length; ++d) {
    const v = s[d];
    if (!o && (v === "-" || v === "+"))
      o = v;
    else {
      const D = Number(v);
      !a && D ? a = D : l === -1 && (l = e + d);
    }
  }
  l !== -1 && r(l, "UNEXPECTED_TOKEN", `Block scalar header includes extra characters: ${s}`);
  let u = !1, f = "", c = s.length;
  for (let d = 1; d < t.length; ++d) {
    const v = t[d];
    switch (v.type) {
      case "space":
        u = !0;
      // fallthrough
      case "newline":
        c += v.source.length;
        break;
      case "comment":
        n && !u && r(v, "MISSING_CHAR", "Comments must be separated from other tokens by white space characters"), c += v.source.length, f = v.source.substring(1);
        break;
      case "error":
        r(v, "UNEXPECTED_TOKEN", v.message), c += v.source.length;
        break;
      /* istanbul ignore next should not happen */
      default: {
        const D = `Unexpected token in block scalar header: ${v.type}`;
        r(v, "UNEXPECTED_TOKEN", D);
        const S = v.source;
        S && typeof S == "string" && (c += S.length);
      }
    }
  }
  return { mode: i, indent: a, chomp: o, comment: f, length: c };
}
function f2(e) {
  const t = e.split(/\n( *)/), n = t[0], r = n.match(/^( *)/), i = [r?.[1] ? [r[1], n.slice(r[1].length)] : ["", n]];
  for (let a = 1; a < t.length; a += 2)
    i.push([t[a], t[a + 1]]);
  return i;
}
function h2(e, t, n) {
  const { offset: r, type: s, source: i, end: a } = e;
  let o, l;
  const u = (d, v, D) => n(r + d, v, D);
  switch (s) {
    case "scalar":
      o = oe.PLAIN, l = d2(i, u);
      break;
    case "single-quoted-scalar":
      o = oe.QUOTE_SINGLE, l = m2(i, u);
      break;
    case "double-quoted-scalar":
      o = oe.QUOTE_DOUBLE, l = p2(i, u);
      break;
    /* istanbul ignore next should not happen */
    default:
      return n(e, "UNEXPECTED_TOKEN", `Expected a flow scalar value, but found: ${s}`), {
        value: "",
        type: null,
        comment: "",
        range: [r, r + i.length, r + i.length]
      };
  }
  const f = r + i.length, c = ni(a, f, t, n);
  return {
    value: l,
    type: o,
    comment: c.comment,
    range: [r, f, c.offset]
  };
}
function d2(e, t) {
  let n = "";
  switch (e[0]) {
    /* istanbul ignore next should not happen */
    case "	":
      n = "a tab character";
      break;
    case ",":
      n = "flow indicator character ,";
      break;
    case "%":
      n = "directive indicator character %";
      break;
    case "|":
    case ">": {
      n = `block scalar indicator ${e[0]}`;
      break;
    }
    case "@":
    case "`": {
      n = `reserved character ${e[0]}`;
      break;
    }
  }
  return n && t(0, "BAD_SCALAR_START", `Plain value cannot start with ${n}`), tm(e);
}
function m2(e, t) {
  return (e[e.length - 1] !== "'" || e.length === 1) && t(e.length, "MISSING_CHAR", "Missing closing 'quote"), tm(e.slice(1, -1)).replace(/''/g, "'");
}
function tm(e) {
  let t, n;
  try {
    t = new RegExp(`(.*?)(?<![ 	])[ 	]*\r?
`, "sy"), n = new RegExp(`[ 	]*(.*?)(?:(?<![ 	])[ 	]*)?\r?
`, "sy");
  } catch {
    t = /(.*?)[ \t]*\r?\n/sy, n = /[ \t]*(.*?)[ \t]*\r?\n/sy;
  }
  let r = t.exec(e);
  if (!r)
    return e;
  let s = r[1], i = " ", a = t.lastIndex;
  for (n.lastIndex = a; r = n.exec(e); )
    r[1] === "" ? i === `
` ? s += i : i = `
` : (s += i + r[1], i = " "), a = n.lastIndex;
  const o = /[ \t]*(.*)/sy;
  return o.lastIndex = a, r = o.exec(e), s + i + (r?.[1] ?? "");
}
function p2(e, t) {
  let n = "";
  for (let r = 1; r < e.length - 1; ++r) {
    const s = e[r];
    if (!(s === "\r" && e[r + 1] === `
`))
      if (s === `
`) {
        const { fold: i, offset: a } = g2(e, r);
        n += i, r = a;
      } else if (s === "\\") {
        let i = e[++r];
        const a = y2[i];
        if (a)
          n += a;
        else if (i === `
`)
          for (i = e[r + 1]; i === " " || i === "	"; )
            i = e[++r + 1];
        else if (i === "\r" && e[r + 1] === `
`)
          for (i = e[++r + 1]; i === " " || i === "	"; )
            i = e[++r + 1];
        else if (i === "x" || i === "u" || i === "U") {
          const o = { x: 2, u: 4, U: 8 }[i];
          n += b2(e, r + 1, o, t), r += o;
        } else {
          const o = e.substr(r - 1, 2);
          t(r - 1, "BAD_DQ_ESCAPE", `Invalid escape sequence ${o}`), n += o;
        }
      } else if (s === " " || s === "	") {
        const i = r;
        let a = e[r + 1];
        for (; a === " " || a === "	"; )
          a = e[++r + 1];
        a !== `
` && !(a === "\r" && e[r + 2] === `
`) && (n += r > i ? e.slice(i, r + 1) : s);
      } else
        n += s;
  }
  return (e[e.length - 1] !== '"' || e.length === 1) && t(e.length, "MISSING_CHAR", 'Missing closing "quote'), n;
}
function g2(e, t) {
  let n = "", r = e[t + 1];
  for (; (r === " " || r === "	" || r === `
` || r === "\r") && !(r === "\r" && e[t + 2] !== `
`); )
    r === `
` && (n += `
`), t += 1, r = e[t + 1];
  return n || (n = " "), { fold: n, offset: t };
}
const y2 = {
  0: "\0",
  // null character
  a: "\x07",
  // bell character
  b: "\b",
  // backspace
  e: "\x1B",
  // escape character
  f: "\f",
  // form feed
  n: `
`,
  // line feed
  r: "\r",
  // carriage return
  t: "	",
  // horizontal tab
  v: "\v",
  // vertical tab
  N: "",
  // Unicode next line
  _: " ",
  // Unicode non-breaking space
  L: "\u2028",
  // Unicode line separator
  P: "\u2029",
  // Unicode paragraph separator
  " ": " ",
  '"': '"',
  "/": "/",
  "\\": "\\",
  "	": "	"
};
function b2(e, t, n, r) {
  const s = e.substr(t, n), a = s.length === n && /^[0-9a-fA-F]+$/.test(s) ? parseInt(s, 16) : NaN;
  if (isNaN(a)) {
    const o = e.substr(t - 2, n + 2);
    return r(t - 2, "BAD_DQ_ESCAPE", `Invalid escape sequence ${o}`), o;
  }
  return String.fromCodePoint(a);
}
function nm(e, t, n, r) {
  const { value: s, type: i, comment: a, range: o } = t.type === "block-scalar" ? u2(e, t, r) : h2(t, e.options.strict, r), l = n ? e.directives.tagName(n.source, (c) => r(n, "TAG_RESOLVE_FAILED", c)) : null;
  let u;
  e.options.stringKeys && e.atKey ? u = e.schema[Qt] : l ? u = v2(e.schema, s, l, n, r) : t.type === "scalar" ? u = w2(e, s, t, r) : u = e.schema[Qt];
  let f;
  try {
    const c = u.resolve(s, (d) => r(n ?? t, "TAG_RESOLVE_FAILED", d), e.options);
    f = ae(c) ? c : new oe(c);
  } catch (c) {
    const d = c instanceof Error ? c.message : String(c);
    r(n ?? t, "TAG_RESOLVE_FAILED", d), f = new oe(s);
  }
  return f.range = o, f.source = s, i && (f.type = i), l && (f.tag = l), u.format && (f.format = u.format), a && (f.comment = a), f;
}
function v2(e, t, n, r, s) {
  if (n === "!")
    return e[Qt];
  const i = [];
  for (const o of e.tags)
    if (!o.collection && o.tag === n)
      if (o.default && o.test)
        i.push(o);
      else
        return o;
  for (const o of i)
    if (o.test?.test(t))
      return o;
  const a = e.knownTags[n];
  return a && !a.collection ? (e.tags.push(Object.assign({}, a, { default: !1, test: void 0 })), a) : (s(r, "TAG_RESOLVE_FAILED", `Unresolved tag: ${n}`, n !== "tag:yaml.org,2002:str"), e[Qt]);
}
function w2({ atKey: e, directives: t, schema: n }, r, s, i) {
  const a = n.tags.find((o) => (o.default === !0 || e && o.default === "key") && o.test?.test(r)) || n[Qt];
  if (n.compat) {
    const o = n.compat.find((l) => l.default && l.test?.test(r)) ?? n[Qt];
    if (a.tag !== o.tag) {
      const l = t.tagString(a.tag), u = t.tagString(o.tag), f = `Value may be parsed as either ${l} or ${u}`;
      i(s, "TAG_RESOLVE_FAILED", f, !0);
    }
  }
  return a;
}
function D2(e, t, n) {
  if (t) {
    n ?? (n = t.length);
    for (let r = n - 1; r >= 0; --r) {
      let s = t[r];
      switch (s.type) {
        case "space":
        case "comment":
        case "newline":
          e -= s.source.length;
          continue;
      }
      for (s = t[++r]; s?.type === "space"; )
        e += s.source.length, s = t[++r];
      break;
    }
  }
  return e;
}
const S2 = { composeNode: rm, composeEmptyNode: Du };
function rm(e, t, n, r) {
  const s = e.atKey, { spaceBefore: i, comment: a, anchor: o, tag: l } = n;
  let u, f = !0;
  switch (t.type) {
    case "alias":
      u = E2(e, t, r), (o || l) && r(t, "ALIAS_PROPS", "An alias node must not specify any properties");
      break;
    case "scalar":
    case "single-quoted-scalar":
    case "double-quoted-scalar":
    case "block-scalar":
      u = nm(e, t, l, r), o && (u.anchor = o.source.substring(1));
      break;
    case "block-map":
    case "block-seq":
    case "flow-collection":
      u = l2(S2, e, t, n, r), o && (u.anchor = o.source.substring(1));
      break;
    default: {
      const c = t.type === "error" ? t.message : `Unsupported token (type: ${t.type})`;
      r(t, "UNEXPECTED_TOKEN", c), u = Du(e, t.offset, void 0, null, n, r), f = !1;
    }
  }
  return o && u.anchor === "" && r(o, "BAD_ALIAS", "Anchor cannot be an empty string"), s && e.options.stringKeys && (!ae(u) || typeof u.value != "string" || u.tag && u.tag !== "tag:yaml.org,2002:str") && r(l ?? t, "NON_STRING_KEY", "With stringKeys, all keys must be strings"), i && (u.spaceBefore = !0), a && (t.type === "scalar" && t.source === "" ? u.comment = a : u.commentBefore = a), e.options.keepSourceTokens && f && (u.srcToken = t), u;
}
function Du(e, t, n, r, { spaceBefore: s, comment: i, anchor: a, tag: o, end: l }, u) {
  const f = {
    type: "scalar",
    offset: D2(t, n, r),
    indent: -1,
    source: ""
  }, c = nm(e, f, o, u);
  return a && (c.anchor = a.source.substring(1), c.anchor === "" && u(a, "BAD_ALIAS", "Anchor cannot be an empty string")), s && (c.spaceBefore = !0), i && (c.comment = i, c.range[2] = l), c;
}
function E2({ options: e }, { offset: t, source: n, end: r }, s) {
  const i = new uu(n.substring(1));
  i.source === "" && s(t, "BAD_ALIAS", "Alias cannot be an empty string"), i.source.endsWith(":") && s(t + n.length - 1, "BAD_ALIAS", "Alias ending in : is ambiguous", !0);
  const a = t + n.length, o = ni(r, a, e.strict, s);
  return i.range = [t, a, o.offset], o.comment && (i.comment = o.comment), i;
}
function A2(e, t, { offset: n, start: r, value: s, end: i }, a) {
  const o = Object.assign({ _directives: t }, e), l = new ti(void 0, o), u = {
    atKey: !1,
    atRoot: !0,
    directives: l.directives,
    options: l.options,
    schema: l.schema
  }, f = ss(r, {
    indicator: "doc-start",
    next: s ?? i?.[0],
    offset: n,
    onError: a,
    parentIndent: 0,
    startOnNewline: !0
  });
  f.found && (l.directives.docStart = !0, s && (s.type === "block-map" || s.type === "block-seq") && !f.hasNewline && a(f.end, "MISSING_CHAR", "Block collection cannot start on same line with directives-end marker")), l.contents = s ? rm(u, s, f, a) : Du(u, f.end, r, null, f, a);
  const c = l.contents.range[2], d = ni(i, c, !1, a);
  return d.comment && (l.comment = d.comment), l.range = [n, c, d.offset], l;
}
function Ds(e) {
  if (typeof e == "number")
    return [e, e + 1];
  if (Array.isArray(e))
    return e.length === 2 ? e : [e[0], e[1]];
  const { offset: t, source: n } = e;
  return [t, t + (typeof n == "string" ? n.length : 1)];
}
function Hh(e) {
  let t = "", n = !1, r = !1;
  for (let s = 0; s < e.length; ++s) {
    const i = e[s];
    switch (i[0]) {
      case "#":
        t += (t === "" ? "" : r ? `

` : `
`) + (i.substring(1) || " "), n = !0, r = !1;
        break;
      case "%":
        e[s + 1]?.[0] !== "#" && (s += 1), n = !1;
        break;
      default:
        n || (r = !0), n = !1;
    }
  }
  return { comment: t, afterEmptyLine: r };
}
class sm {
  constructor(t = {}) {
    this.doc = null, this.atDirectives = !1, this.prelude = [], this.errors = [], this.warnings = [], this.onError = (n, r, s, i) => {
      const a = Ds(n);
      i ? this.warnings.push(new s2(a, r, s)) : this.errors.push(new ks(a, r, s));
    }, this.directives = new Ze({ version: t.version || "1.2" }), this.options = t;
  }
  decorate(t, n) {
    const { comment: r, afterEmptyLine: s } = Hh(this.prelude);
    if (r) {
      const i = t.contents;
      if (n)
        t.comment = t.comment ? `${t.comment}
${r}` : r;
      else if (s || t.directives.docStart || !i)
        t.commentBefore = r;
      else if (Pe(i) && !i.flow && i.items.length > 0) {
        let a = i.items[0];
        Ae(a) && (a = a.key);
        const o = a.commentBefore;
        a.commentBefore = o ? `${r}
${o}` : r;
      } else {
        const a = i.commentBefore;
        i.commentBefore = a ? `${r}
${a}` : r;
      }
    }
    n ? (Array.prototype.push.apply(t.errors, this.errors), Array.prototype.push.apply(t.warnings, this.warnings)) : (t.errors = this.errors, t.warnings = this.warnings), this.prelude = [], this.errors = [], this.warnings = [];
  }
  /**
   * Current stream status information.
   *
   * Mostly useful at the end of input for an empty stream.
   */
  streamInfo() {
    return {
      comment: Hh(this.prelude).comment,
      directives: this.directives,
      errors: this.errors,
      warnings: this.warnings
    };
  }
  /**
   * Compose tokens into documents.
   *
   * @param forceDoc - If the stream contains no document, still emit a final document including any comments and directives that would be applied to a subsequent document.
   * @param endOffset - Should be set if `forceDoc` is also set, to set the document range end and to indicate errors correctly.
   */
  *compose(t, n = !1, r = -1) {
    for (const s of t)
      yield* this.next(s);
    yield* this.end(n, r);
  }
  /** Advance the composer by one CST token. */
  *next(t) {
    switch (t.type) {
      case "directive":
        this.directives.add(t.source, (n, r, s) => {
          const i = Ds(t);
          i[0] += n, this.onError(i, "BAD_DIRECTIVE", r, s);
        }), this.prelude.push(t.source), this.atDirectives = !0;
        break;
      case "document": {
        const n = A2(this.options, this.directives, t, this.onError);
        this.atDirectives && !n.directives.docStart && this.onError(t, "MISSING_CHAR", "Missing directives-end/doc-start indicator line"), this.decorate(n, !1), this.doc && (yield this.doc), this.doc = n, this.atDirectives = !1;
        break;
      }
      case "byte-order-mark":
      case "space":
        break;
      case "comment":
      case "newline":
        this.prelude.push(t.source);
        break;
      case "error": {
        const n = t.source ? `${t.message}: ${JSON.stringify(t.source)}` : t.message, r = new ks(Ds(t), "UNEXPECTED_TOKEN", n);
        this.atDirectives || !this.doc ? this.errors.push(r) : this.doc.errors.push(r);
        break;
      }
      case "doc-end": {
        if (!this.doc) {
          const r = "Unexpected doc-end without preceding document";
          this.errors.push(new ks(Ds(t), "UNEXPECTED_TOKEN", r));
          break;
        }
        this.doc.directives.docEnd = !0;
        const n = ni(t.end, t.offset + t.source.length, this.doc.options.strict, this.onError);
        if (this.decorate(this.doc, !0), n.comment) {
          const r = this.doc.comment;
          this.doc.comment = r ? `${r}
${n.comment}` : n.comment;
        }
        this.doc.range[2] = n.offset;
        break;
      }
      default:
        this.errors.push(new ks(Ds(t), "UNEXPECTED_TOKEN", `Unsupported token ${t.type}`));
    }
  }
  /**
   * Call at end of input to yield any remaining document.
   *
   * @param forceDoc - If the stream contains no document, still emit a final document including any comments and directives that would be applied to a subsequent document.
   * @param endOffset - Should be set if `forceDoc` is also set, to set the document range end and to indicate errors correctly.
   */
  *end(t = !1, n = -1) {
    if (this.doc)
      this.decorate(this.doc, !0), yield this.doc, this.doc = null;
    else if (t) {
      const r = Object.assign({ _directives: this.directives }, this.options), s = new ti(void 0, r);
      this.atDirectives && this.onError(n, "MISSING_CHAR", "Missing directives-end indicator line"), s.range = [0, n, n], this.decorate(s, !1), yield s;
    }
  }
}
const im = (e) => "type" in e ? la(e) : Oi(e);
function la(e) {
  switch (e.type) {
    case "block-scalar": {
      let t = "";
      for (const n of e.props)
        t += la(n);
      return t + e.source;
    }
    case "block-map":
    case "block-seq": {
      let t = "";
      for (const n of e.items)
        t += Oi(n);
      return t;
    }
    case "flow-collection": {
      let t = e.start.source;
      for (const n of e.items)
        t += Oi(n);
      for (const n of e.end)
        t += n.source;
      return t;
    }
    case "document": {
      let t = Oi(e);
      if (e.end)
        for (const n of e.end)
          t += n.source;
      return t;
    }
    default: {
      let t = e.source;
      if ("end" in e && e.end)
        for (const n of e.end)
          t += n.source;
      return t;
    }
  }
}
function Oi({ start: e, key: t, sep: n, value: r }) {
  let s = "";
  for (const i of e)
    s += i.source;
  if (t && (s += la(t)), n)
    for (const i of n)
      s += i.source;
  return r && (s += la(r)), s;
}
const Nl = Symbol("break visit"), x2 = Symbol("skip children"), am = Symbol("remove item");
function or(e, t) {
  "type" in e && e.type === "document" && (e = { start: e.start, value: e.value }), om(Object.freeze([]), e, t);
}
or.BREAK = Nl;
or.SKIP = x2;
or.REMOVE = am;
or.itemAtPath = (e, t) => {
  let n = e;
  for (const [r, s] of t) {
    const i = n?.[r];
    if (i && "items" in i)
      n = i.items[s];
    else
      return;
  }
  return n;
};
or.parentCollection = (e, t) => {
  const n = or.itemAtPath(e, t.slice(0, -1)), r = t[t.length - 1][0], s = n?.[r];
  if (s && "items" in s)
    return s;
  throw new Error("Parent collection not found");
};
function om(e, t, n) {
  let r = n(t, e);
  if (typeof r == "symbol")
    return r;
  for (const s of ["key", "value"]) {
    const i = t[s];
    if (i && "items" in i) {
      for (let a = 0; a < i.items.length; ++a) {
        const o = om(Object.freeze(e.concat([[s, a]])), i.items[a], n);
        if (typeof o == "number")
          a = o - 1;
        else {
          if (o === Nl)
            return Nl;
          o === am && (i.items.splice(a, 1), a -= 1);
        }
      }
      typeof r == "function" && s === "key" && (r = r(t, e));
    }
  }
  return typeof r == "function" ? r(t, e) : r;
}
const lm = "\uFEFF", um = "", cm = "", Ll = "", N2 = (e) => !!e && "items" in e, io = (e) => !!e && (e.type === "scalar" || e.type === "single-quoted-scalar" || e.type === "double-quoted-scalar" || e.type === "block-scalar");
function L2(e) {
  switch (e) {
    case lm:
      return "byte-order-mark";
    case um:
      return "doc-mode";
    case cm:
      return "flow-error-end";
    case Ll:
      return "scalar";
    case "---":
      return "doc-start";
    case "...":
      return "doc-end";
    case "":
    case `
`:
    case `\r
`:
      return "newline";
    case "-":
      return "seq-item-ind";
    case "?":
      return "explicit-key-ind";
    case ":":
      return "map-value-ind";
    case "{":
      return "flow-map-start";
    case "}":
      return "flow-map-end";
    case "[":
      return "flow-seq-start";
    case "]":
      return "flow-seq-end";
    case ",":
      return "comma";
  }
  switch (e[0]) {
    case " ":
    case "	":
      return "space";
    case "#":
      return "comment";
    case "%":
      return "directive-line";
    case "*":
      return "alias";
    case "&":
      return "anchor";
    case "!":
      return "tag";
    case "'":
      return "single-quoted-scalar";
    case '"':
      return "double-quoted-scalar";
    case "|":
    case ">":
      return "block-scalar-header";
  }
  return null;
}
function Tt(e) {
  switch (e) {
    case void 0:
    case " ":
    case `
`:
    case "\r":
    case "	":
      return !0;
    default:
      return !1;
  }
}
const Yh = new Set("0123456789ABCDEFabcdef"), k2 = new Set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-#;/?:@&=+$_.!~*'()"), pi = new Set(",[]{}"), C2 = new Set(` ,[]{}
\r	`), ao = (e) => !e || C2.has(e);
class F2 {
  constructor() {
    this.atEnd = !1, this.blockScalarIndent = -1, this.blockScalarKeep = !1, this.buffer = "", this.flowKey = !1, this.flowLevel = 0, this.indentNext = 0, this.indentValue = 0, this.lineEndPos = null, this.next = null, this.pos = 0;
  }
  /**
   * Generate YAML tokens from the `source` string. If `incomplete`,
   * a part of the last line may be left as a buffer for the next call.
   *
   * @returns A generator of lexical tokens
   */
  *lex(t, n = !1) {
    if (t) {
      if (typeof t != "string")
        throw TypeError("source is not a string");
      this.buffer = this.buffer ? this.buffer + t : t, this.lineEndPos = null;
    }
    this.atEnd = !n;
    let r = this.next ?? "stream";
    for (; r && (n || this.hasChars(1)); )
      r = yield* this.parseNext(r);
  }
  atLineEnd() {
    let t = this.pos, n = this.buffer[t];
    for (; n === " " || n === "	"; )
      n = this.buffer[++t];
    return !n || n === "#" || n === `
` ? !0 : n === "\r" ? this.buffer[t + 1] === `
` : !1;
  }
  charAt(t) {
    return this.buffer[this.pos + t];
  }
  continueScalar(t) {
    let n = this.buffer[t];
    if (this.indentNext > 0) {
      let r = 0;
      for (; n === " "; )
        n = this.buffer[++r + t];
      if (n === "\r") {
        const s = this.buffer[r + t + 1];
        if (s === `
` || !s && !this.atEnd)
          return t + r + 1;
      }
      return n === `
` || r >= this.indentNext || !n && !this.atEnd ? t + r : -1;
    }
    if (n === "-" || n === ".") {
      const r = this.buffer.substr(t, 3);
      if ((r === "---" || r === "...") && Tt(this.buffer[t + 3]))
        return -1;
    }
    return t;
  }
  getLine() {
    let t = this.lineEndPos;
    return (typeof t != "number" || t !== -1 && t < this.pos) && (t = this.buffer.indexOf(`
`, this.pos), this.lineEndPos = t), t === -1 ? this.atEnd ? this.buffer.substring(this.pos) : null : (this.buffer[t - 1] === "\r" && (t -= 1), this.buffer.substring(this.pos, t));
  }
  hasChars(t) {
    return this.pos + t <= this.buffer.length;
  }
  setNext(t) {
    return this.buffer = this.buffer.substring(this.pos), this.pos = 0, this.lineEndPos = null, this.next = t, null;
  }
  peek(t) {
    return this.buffer.substr(this.pos, t);
  }
  *parseNext(t) {
    switch (t) {
      case "stream":
        return yield* this.parseStream();
      case "line-start":
        return yield* this.parseLineStart();
      case "block-start":
        return yield* this.parseBlockStart();
      case "doc":
        return yield* this.parseDocument();
      case "flow":
        return yield* this.parseFlowCollection();
      case "quoted-scalar":
        return yield* this.parseQuotedScalar();
      case "block-scalar":
        return yield* this.parseBlockScalar();
      case "plain-scalar":
        return yield* this.parsePlainScalar();
    }
  }
  *parseStream() {
    let t = this.getLine();
    if (t === null)
      return this.setNext("stream");
    if (t[0] === lm && (yield* this.pushCount(1), t = t.substring(1)), t[0] === "%") {
      let n = t.length, r = t.indexOf("#");
      for (; r !== -1; ) {
        const i = t[r - 1];
        if (i === " " || i === "	") {
          n = r - 1;
          break;
        } else
          r = t.indexOf("#", r + 1);
      }
      for (; ; ) {
        const i = t[n - 1];
        if (i === " " || i === "	")
          n -= 1;
        else
          break;
      }
      const s = (yield* this.pushCount(n)) + (yield* this.pushSpaces(!0));
      return yield* this.pushCount(t.length - s), this.pushNewline(), "stream";
    }
    if (this.atLineEnd()) {
      const n = yield* this.pushSpaces(!0);
      return yield* this.pushCount(t.length - n), yield* this.pushNewline(), "stream";
    }
    return yield um, yield* this.parseLineStart();
  }
  *parseLineStart() {
    const t = this.charAt(0);
    if (!t && !this.atEnd)
      return this.setNext("line-start");
    if (t === "-" || t === ".") {
      if (!this.atEnd && !this.hasChars(4))
        return this.setNext("line-start");
      const n = this.peek(3);
      if ((n === "---" || n === "...") && Tt(this.charAt(3)))
        return yield* this.pushCount(3), this.indentValue = 0, this.indentNext = 0, n === "---" ? "doc" : "stream";
    }
    return this.indentValue = yield* this.pushSpaces(!1), this.indentNext > this.indentValue && !Tt(this.charAt(1)) && (this.indentNext = this.indentValue), yield* this.parseBlockStart();
  }
  *parseBlockStart() {
    const [t, n] = this.peek(2);
    if (!n && !this.atEnd)
      return this.setNext("block-start");
    if ((t === "-" || t === "?" || t === ":") && Tt(n)) {
      const r = (yield* this.pushCount(1)) + (yield* this.pushSpaces(!0));
      return this.indentNext = this.indentValue + 1, this.indentValue += r, yield* this.parseBlockStart();
    }
    return "doc";
  }
  *parseDocument() {
    yield* this.pushSpaces(!0);
    const t = this.getLine();
    if (t === null)
      return this.setNext("doc");
    let n = yield* this.pushIndicators();
    switch (t[n]) {
      case "#":
        yield* this.pushCount(t.length - n);
      // fallthrough
      case void 0:
        return yield* this.pushNewline(), yield* this.parseLineStart();
      case "{":
      case "[":
        return yield* this.pushCount(1), this.flowKey = !1, this.flowLevel = 1, "flow";
      case "}":
      case "]":
        return yield* this.pushCount(1), "doc";
      case "*":
        return yield* this.pushUntil(ao), "doc";
      case '"':
      case "'":
        return yield* this.parseQuotedScalar();
      case "|":
      case ">":
        return n += yield* this.parseBlockScalarHeader(), n += yield* this.pushSpaces(!0), yield* this.pushCount(t.length - n), yield* this.pushNewline(), yield* this.parseBlockScalar();
      default:
        return yield* this.parsePlainScalar();
    }
  }
  *parseFlowCollection() {
    let t, n, r = -1;
    do
      t = yield* this.pushNewline(), t > 0 ? (n = yield* this.pushSpaces(!1), this.indentValue = r = n) : n = 0, n += yield* this.pushSpaces(!0);
    while (t + n > 0);
    const s = this.getLine();
    if (s === null)
      return this.setNext("flow");
    if ((r !== -1 && r < this.indentNext && s[0] !== "#" || r === 0 && (s.startsWith("---") || s.startsWith("...")) && Tt(s[3])) && !(r === this.indentNext - 1 && this.flowLevel === 1 && (s[0] === "]" || s[0] === "}")))
      return this.flowLevel = 0, yield cm, yield* this.parseLineStart();
    let i = 0;
    for (; s[i] === ","; )
      i += yield* this.pushCount(1), i += yield* this.pushSpaces(!0), this.flowKey = !1;
    switch (i += yield* this.pushIndicators(), s[i]) {
      case void 0:
        return "flow";
      case "#":
        return yield* this.pushCount(s.length - i), "flow";
      case "{":
      case "[":
        return yield* this.pushCount(1), this.flowKey = !1, this.flowLevel += 1, "flow";
      case "}":
      case "]":
        return yield* this.pushCount(1), this.flowKey = !0, this.flowLevel -= 1, this.flowLevel ? "flow" : "doc";
      case "*":
        return yield* this.pushUntil(ao), "flow";
      case '"':
      case "'":
        return this.flowKey = !0, yield* this.parseQuotedScalar();
      case ":": {
        const a = this.charAt(1);
        if (this.flowKey || Tt(a) || a === ",")
          return this.flowKey = !1, yield* this.pushCount(1), yield* this.pushSpaces(!0), "flow";
      }
      // fallthrough
      default:
        return this.flowKey = !1, yield* this.parsePlainScalar();
    }
  }
  *parseQuotedScalar() {
    const t = this.charAt(0);
    let n = this.buffer.indexOf(t, this.pos + 1);
    if (t === "'")
      for (; n !== -1 && this.buffer[n + 1] === "'"; )
        n = this.buffer.indexOf("'", n + 2);
    else
      for (; n !== -1; ) {
        let i = 0;
        for (; this.buffer[n - 1 - i] === "\\"; )
          i += 1;
        if (i % 2 === 0)
          break;
        n = this.buffer.indexOf('"', n + 1);
      }
    const r = this.buffer.substring(0, n);
    let s = r.indexOf(`
`, this.pos);
    if (s !== -1) {
      for (; s !== -1; ) {
        const i = this.continueScalar(s + 1);
        if (i === -1)
          break;
        s = r.indexOf(`
`, i);
      }
      s !== -1 && (n = s - (r[s - 1] === "\r" ? 2 : 1));
    }
    if (n === -1) {
      if (!this.atEnd)
        return this.setNext("quoted-scalar");
      n = this.buffer.length;
    }
    return yield* this.pushToIndex(n + 1, !1), this.flowLevel ? "flow" : "doc";
  }
  *parseBlockScalarHeader() {
    this.blockScalarIndent = -1, this.blockScalarKeep = !1;
    let t = this.pos;
    for (; ; ) {
      const n = this.buffer[++t];
      if (n === "+")
        this.blockScalarKeep = !0;
      else if (n > "0" && n <= "9")
        this.blockScalarIndent = Number(n) - 1;
      else if (n !== "-")
        break;
    }
    return yield* this.pushUntil((n) => Tt(n) || n === "#");
  }
  *parseBlockScalar() {
    let t = this.pos - 1, n = 0, r;
    e: for (let i = this.pos; r = this.buffer[i]; ++i)
      switch (r) {
        case " ":
          n += 1;
          break;
        case `
`:
          t = i, n = 0;
          break;
        case "\r": {
          const a = this.buffer[i + 1];
          if (!a && !this.atEnd)
            return this.setNext("block-scalar");
          if (a === `
`)
            break;
        }
        // fallthrough
        default:
          break e;
      }
    if (!r && !this.atEnd)
      return this.setNext("block-scalar");
    if (n >= this.indentNext) {
      this.blockScalarIndent === -1 ? this.indentNext = n : this.indentNext = this.blockScalarIndent + (this.indentNext === 0 ? 1 : this.indentNext);
      do {
        const i = this.continueScalar(t + 1);
        if (i === -1)
          break;
        t = this.buffer.indexOf(`
`, i);
      } while (t !== -1);
      if (t === -1) {
        if (!this.atEnd)
          return this.setNext("block-scalar");
        t = this.buffer.length;
      }
    }
    let s = t + 1;
    for (r = this.buffer[s]; r === " "; )
      r = this.buffer[++s];
    if (r === "	") {
      for (; r === "	" || r === " " || r === "\r" || r === `
`; )
        r = this.buffer[++s];
      t = s - 1;
    } else if (!this.blockScalarKeep)
      do {
        let i = t - 1, a = this.buffer[i];
        a === "\r" && (a = this.buffer[--i]);
        const o = i;
        for (; a === " "; )
          a = this.buffer[--i];
        if (a === `
` && i >= this.pos && i + 1 + n > o)
          t = i;
        else
          break;
      } while (!0);
    return yield Ll, yield* this.pushToIndex(t + 1, !0), yield* this.parseLineStart();
  }
  *parsePlainScalar() {
    const t = this.flowLevel > 0;
    let n = this.pos - 1, r = this.pos - 1, s;
    for (; s = this.buffer[++r]; )
      if (s === ":") {
        const i = this.buffer[r + 1];
        if (Tt(i) || t && pi.has(i))
          break;
        n = r;
      } else if (Tt(s)) {
        let i = this.buffer[r + 1];
        if (s === "\r" && (i === `
` ? (r += 1, s = `
`, i = this.buffer[r + 1]) : n = r), i === "#" || t && pi.has(i))
          break;
        if (s === `
`) {
          const a = this.continueScalar(r + 1);
          if (a === -1)
            break;
          r = Math.max(r, a - 2);
        }
      } else {
        if (t && pi.has(s))
          break;
        n = r;
      }
    return !s && !this.atEnd ? this.setNext("plain-scalar") : (yield Ll, yield* this.pushToIndex(n + 1, !0), t ? "flow" : "doc");
  }
  *pushCount(t) {
    return t > 0 ? (yield this.buffer.substr(this.pos, t), this.pos += t, t) : 0;
  }
  *pushToIndex(t, n) {
    const r = this.buffer.slice(this.pos, t);
    return r ? (yield r, this.pos += r.length, r.length) : (n && (yield ""), 0);
  }
  *pushIndicators() {
    switch (this.charAt(0)) {
      case "!":
        return (yield* this.pushTag()) + (yield* this.pushSpaces(!0)) + (yield* this.pushIndicators());
      case "&":
        return (yield* this.pushUntil(ao)) + (yield* this.pushSpaces(!0)) + (yield* this.pushIndicators());
      case "-":
      // this is an error
      case "?":
      // this is an error outside flow collections
      case ":": {
        const t = this.flowLevel > 0, n = this.charAt(1);
        if (Tt(n) || t && pi.has(n))
          return t ? this.flowKey && (this.flowKey = !1) : this.indentNext = this.indentValue + 1, (yield* this.pushCount(1)) + (yield* this.pushSpaces(!0)) + (yield* this.pushIndicators());
      }
    }
    return 0;
  }
  *pushTag() {
    if (this.charAt(1) === "<") {
      let t = this.pos + 2, n = this.buffer[t];
      for (; !Tt(n) && n !== ">"; )
        n = this.buffer[++t];
      return yield* this.pushToIndex(n === ">" ? t + 1 : t, !1);
    } else {
      let t = this.pos + 1, n = this.buffer[t];
      for (; n; )
        if (k2.has(n))
          n = this.buffer[++t];
        else if (n === "%" && Yh.has(this.buffer[t + 1]) && Yh.has(this.buffer[t + 2]))
          n = this.buffer[t += 3];
        else
          break;
      return yield* this.pushToIndex(t, !1);
    }
  }
  *pushNewline() {
    const t = this.buffer[this.pos];
    return t === `
` ? yield* this.pushCount(1) : t === "\r" && this.charAt(1) === `
` ? yield* this.pushCount(2) : 0;
  }
  *pushSpaces(t) {
    let n = this.pos - 1, r;
    do
      r = this.buffer[++n];
    while (r === " " || t && r === "	");
    const s = n - this.pos;
    return s > 0 && (yield this.buffer.substr(this.pos, s), this.pos = n), s;
  }
  *pushUntil(t) {
    let n = this.pos, r = this.buffer[n];
    for (; !t(r); )
      r = this.buffer[++n];
    return yield* this.pushToIndex(n, !1);
  }
}
class fm {
  constructor() {
    this.lineStarts = [], this.addNewLine = (t) => this.lineStarts.push(t), this.linePos = (t) => {
      let n = 0, r = this.lineStarts.length;
      for (; n < r; ) {
        const i = n + r >> 1;
        this.lineStarts[i] < t ? n = i + 1 : r = i;
      }
      if (this.lineStarts[n] === t)
        return { line: n + 1, col: 1 };
      if (n === 0)
        return { line: 0, col: t };
      const s = this.lineStarts[n - 1];
      return { line: n, col: t - s + 1 };
    };
  }
}
function kn(e, t) {
  for (let n = 0; n < e.length; ++n)
    if (e[n].type === t)
      return !0;
  return !1;
}
function zh(e) {
  for (let t = 0; t < e.length; ++t)
    switch (e[t].type) {
      case "space":
      case "comment":
      case "newline":
        break;
      default:
        return t;
    }
  return -1;
}
function hm(e) {
  switch (e?.type) {
    case "alias":
    case "scalar":
    case "single-quoted-scalar":
    case "double-quoted-scalar":
    case "flow-collection":
      return !0;
    default:
      return !1;
  }
}
function gi(e) {
  switch (e.type) {
    case "document":
      return e.start;
    case "block-map": {
      const t = e.items[e.items.length - 1];
      return t.sep ?? t.start;
    }
    case "block-seq":
      return e.items[e.items.length - 1].start;
    /* istanbul ignore next should not happen */
    default:
      return [];
  }
}
function kr(e) {
  if (e.length === 0)
    return [];
  let t = e.length;
  e: for (; --t >= 0; )
    switch (e[t].type) {
      case "doc-start":
      case "explicit-key-ind":
      case "map-value-ind":
      case "seq-item-ind":
      case "newline":
        break e;
    }
  for (; e[++t]?.type === "space"; )
    ;
  return e.splice(t, e.length);
}
function Gh(e) {
  if (e.start.type === "flow-seq-start")
    for (const t of e.items)
      t.sep && !t.value && !kn(t.start, "explicit-key-ind") && !kn(t.sep, "map-value-ind") && (t.key && (t.value = t.key), delete t.key, hm(t.value) ? t.value.end ? Array.prototype.push.apply(t.value.end, t.sep) : t.value.end = t.sep : Array.prototype.push.apply(t.start, t.sep), delete t.sep);
}
class kl {
  /**
   * @param onNewLine - If defined, called separately with the start position of
   *   each new line (in `parse()`, including the start of input).
   */
  constructor(t) {
    this.atNewLine = !0, this.atScalar = !1, this.indent = 0, this.offset = 0, this.onKeyLine = !1, this.stack = [], this.source = "", this.type = "", this.lexer = new F2(), this.onNewLine = t;
  }
  /**
   * Parse `source` as a YAML stream.
   * If `incomplete`, a part of the last line may be left as a buffer for the next call.
   *
   * Errors are not thrown, but yielded as `{ type: 'error', message }` tokens.
   *
   * @returns A generator of tokens representing each directive, document, and other structure.
   */
  *parse(t, n = !1) {
    this.onNewLine && this.offset === 0 && this.onNewLine(0);
    for (const r of this.lexer.lex(t, n))
      yield* this.next(r);
    n || (yield* this.end());
  }
  /**
   * Advance the parser by the `source` of one lexical token.
   */
  *next(t) {
    if (this.source = t, this.atScalar) {
      this.atScalar = !1, yield* this.step(), this.offset += t.length;
      return;
    }
    const n = L2(t);
    if (n)
      if (n === "scalar")
        this.atNewLine = !1, this.atScalar = !0, this.type = "scalar";
      else {
        switch (this.type = n, yield* this.step(), n) {
          case "newline":
            this.atNewLine = !0, this.indent = 0, this.onNewLine && this.onNewLine(this.offset + t.length);
            break;
          case "space":
            this.atNewLine && t[0] === " " && (this.indent += t.length);
            break;
          case "explicit-key-ind":
          case "map-value-ind":
          case "seq-item-ind":
            this.atNewLine && (this.indent += t.length);
            break;
          case "doc-mode":
          case "flow-error-end":
            return;
          default:
            this.atNewLine = !1;
        }
        this.offset += t.length;
      }
    else {
      const r = `Not a YAML token: ${t}`;
      yield* this.pop({ type: "error", offset: this.offset, message: r, source: t }), this.offset += t.length;
    }
  }
  /** Call at end of input to push out any remaining constructions */
  *end() {
    for (; this.stack.length > 0; )
      yield* this.pop();
  }
  get sourceToken() {
    return {
      type: this.type,
      offset: this.offset,
      indent: this.indent,
      source: this.source
    };
  }
  *step() {
    const t = this.peek(1);
    if (this.type === "doc-end" && (!t || t.type !== "doc-end")) {
      for (; this.stack.length > 0; )
        yield* this.pop();
      this.stack.push({
        type: "doc-end",
        offset: this.offset,
        source: this.source
      });
      return;
    }
    if (!t)
      return yield* this.stream();
    switch (t.type) {
      case "document":
        return yield* this.document(t);
      case "alias":
      case "scalar":
      case "single-quoted-scalar":
      case "double-quoted-scalar":
        return yield* this.scalar(t);
      case "block-scalar":
        return yield* this.blockScalar(t);
      case "block-map":
        return yield* this.blockMap(t);
      case "block-seq":
        return yield* this.blockSequence(t);
      case "flow-collection":
        return yield* this.flowCollection(t);
      case "doc-end":
        return yield* this.documentEnd(t);
    }
    yield* this.pop();
  }
  peek(t) {
    return this.stack[this.stack.length - t];
  }
  *pop(t) {
    const n = t ?? this.stack.pop();
    if (!n)
      yield { type: "error", offset: this.offset, source: "", message: "Tried to pop an empty stack" };
    else if (this.stack.length === 0)
      yield n;
    else {
      const r = this.peek(1);
      switch (n.type === "block-scalar" ? n.indent = "indent" in r ? r.indent : 0 : n.type === "flow-collection" && r.type === "document" && (n.indent = 0), n.type === "flow-collection" && Gh(n), r.type) {
        case "document":
          r.value = n;
          break;
        case "block-scalar":
          r.props.push(n);
          break;
        case "block-map": {
          const s = r.items[r.items.length - 1];
          if (s.value) {
            r.items.push({ start: [], key: n, sep: [] }), this.onKeyLine = !0;
            return;
          } else if (s.sep)
            s.value = n;
          else {
            Object.assign(s, { key: n, sep: [] }), this.onKeyLine = !s.explicitKey;
            return;
          }
          break;
        }
        case "block-seq": {
          const s = r.items[r.items.length - 1];
          s.value ? r.items.push({ start: [], value: n }) : s.value = n;
          break;
        }
        case "flow-collection": {
          const s = r.items[r.items.length - 1];
          !s || s.value ? r.items.push({ start: [], key: n, sep: [] }) : s.sep ? s.value = n : Object.assign(s, { key: n, sep: [] });
          return;
        }
        /* istanbul ignore next should not happen */
        default:
          yield* this.pop(), yield* this.pop(n);
      }
      if ((r.type === "document" || r.type === "block-map" || r.type === "block-seq") && (n.type === "block-map" || n.type === "block-seq")) {
        const s = n.items[n.items.length - 1];
        s && !s.sep && !s.value && s.start.length > 0 && zh(s.start) === -1 && (n.indent === 0 || s.start.every((i) => i.type !== "comment" || i.indent < n.indent)) && (r.type === "document" ? r.end = s.start : r.items.push({ start: s.start }), n.items.splice(-1, 1));
      }
    }
  }
  *stream() {
    switch (this.type) {
      case "directive-line":
        yield { type: "directive", offset: this.offset, source: this.source };
        return;
      case "byte-order-mark":
      case "space":
      case "comment":
      case "newline":
        yield this.sourceToken;
        return;
      case "doc-mode":
      case "doc-start": {
        const t = {
          type: "document",
          offset: this.offset,
          start: []
        };
        this.type === "doc-start" && t.start.push(this.sourceToken), this.stack.push(t);
        return;
      }
    }
    yield {
      type: "error",
      offset: this.offset,
      message: `Unexpected ${this.type} token in YAML stream`,
      source: this.source
    };
  }
  *document(t) {
    if (t.value)
      return yield* this.lineEnd(t);
    switch (this.type) {
      case "doc-start": {
        zh(t.start) !== -1 ? (yield* this.pop(), yield* this.step()) : t.start.push(this.sourceToken);
        return;
      }
      case "anchor":
      case "tag":
      case "space":
      case "comment":
      case "newline":
        t.start.push(this.sourceToken);
        return;
    }
    const n = this.startBlockValue(t);
    n ? this.stack.push(n) : yield {
      type: "error",
      offset: this.offset,
      message: `Unexpected ${this.type} token in YAML document`,
      source: this.source
    };
  }
  *scalar(t) {
    if (this.type === "map-value-ind") {
      const n = gi(this.peek(2)), r = kr(n);
      let s;
      t.end ? (s = t.end, s.push(this.sourceToken), delete t.end) : s = [this.sourceToken];
      const i = {
        type: "block-map",
        offset: t.offset,
        indent: t.indent,
        items: [{ start: r, key: t, sep: s }]
      };
      this.onKeyLine = !0, this.stack[this.stack.length - 1] = i;
    } else
      yield* this.lineEnd(t);
  }
  *blockScalar(t) {
    switch (this.type) {
      case "space":
      case "comment":
      case "newline":
        t.props.push(this.sourceToken);
        return;
      case "scalar":
        if (t.source = this.source, this.atNewLine = !0, this.indent = 0, this.onNewLine) {
          let n = this.source.indexOf(`
`) + 1;
          for (; n !== 0; )
            this.onNewLine(this.offset + n), n = this.source.indexOf(`
`, n) + 1;
        }
        yield* this.pop();
        break;
      /* istanbul ignore next should not happen */
      default:
        yield* this.pop(), yield* this.step();
    }
  }
  *blockMap(t) {
    const n = t.items[t.items.length - 1];
    switch (this.type) {
      case "newline":
        if (this.onKeyLine = !1, n.value) {
          const r = "end" in n.value ? n.value.end : void 0;
          (Array.isArray(r) ? r[r.length - 1] : void 0)?.type === "comment" ? r?.push(this.sourceToken) : t.items.push({ start: [this.sourceToken] });
        } else n.sep ? n.sep.push(this.sourceToken) : n.start.push(this.sourceToken);
        return;
      case "space":
      case "comment":
        if (n.value)
          t.items.push({ start: [this.sourceToken] });
        else if (n.sep)
          n.sep.push(this.sourceToken);
        else {
          if (this.atIndentedComment(n.start, t.indent)) {
            const s = t.items[t.items.length - 2]?.value?.end;
            if (Array.isArray(s)) {
              Array.prototype.push.apply(s, n.start), s.push(this.sourceToken), t.items.pop();
              return;
            }
          }
          n.start.push(this.sourceToken);
        }
        return;
    }
    if (this.indent >= t.indent) {
      const r = !this.onKeyLine && this.indent === t.indent, s = r && (n.sep || n.explicitKey) && this.type !== "seq-item-ind";
      let i = [];
      if (s && n.sep && !n.value) {
        const a = [];
        for (let o = 0; o < n.sep.length; ++o) {
          const l = n.sep[o];
          switch (l.type) {
            case "newline":
              a.push(o);
              break;
            case "space":
              break;
            case "comment":
              l.indent > t.indent && (a.length = 0);
              break;
            default:
              a.length = 0;
          }
        }
        a.length >= 2 && (i = n.sep.splice(a[1]));
      }
      switch (this.type) {
        case "anchor":
        case "tag":
          s || n.value ? (i.push(this.sourceToken), t.items.push({ start: i }), this.onKeyLine = !0) : n.sep ? n.sep.push(this.sourceToken) : n.start.push(this.sourceToken);
          return;
        case "explicit-key-ind":
          !n.sep && !n.explicitKey ? (n.start.push(this.sourceToken), n.explicitKey = !0) : s || n.value ? (i.push(this.sourceToken), t.items.push({ start: i, explicitKey: !0 })) : this.stack.push({
            type: "block-map",
            offset: this.offset,
            indent: this.indent,
            items: [{ start: [this.sourceToken], explicitKey: !0 }]
          }), this.onKeyLine = !0;
          return;
        case "map-value-ind":
          if (n.explicitKey)
            if (n.sep)
              if (n.value)
                t.items.push({ start: [], key: null, sep: [this.sourceToken] });
              else if (kn(n.sep, "map-value-ind"))
                this.stack.push({
                  type: "block-map",
                  offset: this.offset,
                  indent: this.indent,
                  items: [{ start: i, key: null, sep: [this.sourceToken] }]
                });
              else if (hm(n.key) && !kn(n.sep, "newline")) {
                const a = kr(n.start), o = n.key, l = n.sep;
                l.push(this.sourceToken), delete n.key, delete n.sep, this.stack.push({
                  type: "block-map",
                  offset: this.offset,
                  indent: this.indent,
                  items: [{ start: a, key: o, sep: l }]
                });
              } else i.length > 0 ? n.sep = n.sep.concat(i, this.sourceToken) : n.sep.push(this.sourceToken);
            else if (kn(n.start, "newline"))
              Object.assign(n, { key: null, sep: [this.sourceToken] });
            else {
              const a = kr(n.start);
              this.stack.push({
                type: "block-map",
                offset: this.offset,
                indent: this.indent,
                items: [{ start: a, key: null, sep: [this.sourceToken] }]
              });
            }
          else
            n.sep ? n.value || s ? t.items.push({ start: i, key: null, sep: [this.sourceToken] }) : kn(n.sep, "map-value-ind") ? this.stack.push({
              type: "block-map",
              offset: this.offset,
              indent: this.indent,
              items: [{ start: [], key: null, sep: [this.sourceToken] }]
            }) : n.sep.push(this.sourceToken) : Object.assign(n, { key: null, sep: [this.sourceToken] });
          this.onKeyLine = !0;
          return;
        case "alias":
        case "scalar":
        case "single-quoted-scalar":
        case "double-quoted-scalar": {
          const a = this.flowScalar(this.type);
          s || n.value ? (t.items.push({ start: i, key: a, sep: [] }), this.onKeyLine = !0) : n.sep ? this.stack.push(a) : (Object.assign(n, { key: a, sep: [] }), this.onKeyLine = !0);
          return;
        }
        default: {
          const a = this.startBlockValue(t);
          if (a) {
            if (a.type === "block-seq") {
              if (!n.explicitKey && n.sep && !kn(n.sep, "newline")) {
                yield* this.pop({
                  type: "error",
                  offset: this.offset,
                  message: "Unexpected block-seq-ind on same line with key",
                  source: this.source
                });
                return;
              }
            } else r && t.items.push({ start: i });
            this.stack.push(a);
            return;
          }
        }
      }
    }
    yield* this.pop(), yield* this.step();
  }
  *blockSequence(t) {
    const n = t.items[t.items.length - 1];
    switch (this.type) {
      case "newline":
        if (n.value) {
          const r = "end" in n.value ? n.value.end : void 0;
          (Array.isArray(r) ? r[r.length - 1] : void 0)?.type === "comment" ? r?.push(this.sourceToken) : t.items.push({ start: [this.sourceToken] });
        } else
          n.start.push(this.sourceToken);
        return;
      case "space":
      case "comment":
        if (n.value)
          t.items.push({ start: [this.sourceToken] });
        else {
          if (this.atIndentedComment(n.start, t.indent)) {
            const s = t.items[t.items.length - 2]?.value?.end;
            if (Array.isArray(s)) {
              Array.prototype.push.apply(s, n.start), s.push(this.sourceToken), t.items.pop();
              return;
            }
          }
          n.start.push(this.sourceToken);
        }
        return;
      case "anchor":
      case "tag":
        if (n.value || this.indent <= t.indent)
          break;
        n.start.push(this.sourceToken);
        return;
      case "seq-item-ind":
        if (this.indent !== t.indent)
          break;
        n.value || kn(n.start, "seq-item-ind") ? t.items.push({ start: [this.sourceToken] }) : n.start.push(this.sourceToken);
        return;
    }
    if (this.indent > t.indent) {
      const r = this.startBlockValue(t);
      if (r) {
        this.stack.push(r);
        return;
      }
    }
    yield* this.pop(), yield* this.step();
  }
  *flowCollection(t) {
    const n = t.items[t.items.length - 1];
    if (this.type === "flow-error-end") {
      let r;
      do
        yield* this.pop(), r = this.peek(1);
      while (r && r.type === "flow-collection");
    } else if (t.end.length === 0) {
      switch (this.type) {
        case "comma":
        case "explicit-key-ind":
          !n || n.sep ? t.items.push({ start: [this.sourceToken] }) : n.start.push(this.sourceToken);
          return;
        case "map-value-ind":
          !n || n.value ? t.items.push({ start: [], key: null, sep: [this.sourceToken] }) : n.sep ? n.sep.push(this.sourceToken) : Object.assign(n, { key: null, sep: [this.sourceToken] });
          return;
        case "space":
        case "comment":
        case "newline":
        case "anchor":
        case "tag":
          !n || n.value ? t.items.push({ start: [this.sourceToken] }) : n.sep ? n.sep.push(this.sourceToken) : n.start.push(this.sourceToken);
          return;
        case "alias":
        case "scalar":
        case "single-quoted-scalar":
        case "double-quoted-scalar": {
          const s = this.flowScalar(this.type);
          !n || n.value ? t.items.push({ start: [], key: s, sep: [] }) : n.sep ? this.stack.push(s) : Object.assign(n, { key: s, sep: [] });
          return;
        }
        case "flow-map-end":
        case "flow-seq-end":
          t.end.push(this.sourceToken);
          return;
      }
      const r = this.startBlockValue(t);
      r ? this.stack.push(r) : (yield* this.pop(), yield* this.step());
    } else {
      const r = this.peek(2);
      if (r.type === "block-map" && (this.type === "map-value-ind" && r.indent === t.indent || this.type === "newline" && !r.items[r.items.length - 1].sep))
        yield* this.pop(), yield* this.step();
      else if (this.type === "map-value-ind" && r.type !== "flow-collection") {
        const s = gi(r), i = kr(s);
        Gh(t);
        const a = t.end.splice(1, t.end.length);
        a.push(this.sourceToken);
        const o = {
          type: "block-map",
          offset: t.offset,
          indent: t.indent,
          items: [{ start: i, key: t, sep: a }]
        };
        this.onKeyLine = !0, this.stack[this.stack.length - 1] = o;
      } else
        yield* this.lineEnd(t);
    }
  }
  flowScalar(t) {
    if (this.onNewLine) {
      let n = this.source.indexOf(`
`) + 1;
      for (; n !== 0; )
        this.onNewLine(this.offset + n), n = this.source.indexOf(`
`, n) + 1;
    }
    return {
      type: t,
      offset: this.offset,
      indent: this.indent,
      source: this.source
    };
  }
  startBlockValue(t) {
    switch (this.type) {
      case "alias":
      case "scalar":
      case "single-quoted-scalar":
      case "double-quoted-scalar":
        return this.flowScalar(this.type);
      case "block-scalar-header":
        return {
          type: "block-scalar",
          offset: this.offset,
          indent: this.indent,
          props: [this.sourceToken],
          source: ""
        };
      case "flow-map-start":
      case "flow-seq-start":
        return {
          type: "flow-collection",
          offset: this.offset,
          indent: this.indent,
          start: this.sourceToken,
          items: [],
          end: []
        };
      case "seq-item-ind":
        return {
          type: "block-seq",
          offset: this.offset,
          indent: this.indent,
          items: [{ start: [this.sourceToken] }]
        };
      case "explicit-key-ind": {
        this.onKeyLine = !0;
        const n = gi(t), r = kr(n);
        return r.push(this.sourceToken), {
          type: "block-map",
          offset: this.offset,
          indent: this.indent,
          items: [{ start: r, explicitKey: !0 }]
        };
      }
      case "map-value-ind": {
        this.onKeyLine = !0;
        const n = gi(t), r = kr(n);
        return {
          type: "block-map",
          offset: this.offset,
          indent: this.indent,
          items: [{ start: r, key: null, sep: [this.sourceToken] }]
        };
      }
    }
    return null;
  }
  atIndentedComment(t, n) {
    return this.type !== "comment" || this.indent <= n ? !1 : t.every((r) => r.type === "newline" || r.type === "space");
  }
  *documentEnd(t) {
    this.type !== "doc-mode" && (t.end ? t.end.push(this.sourceToken) : t.end = [this.sourceToken], this.type === "newline" && (yield* this.pop()));
  }
  *lineEnd(t) {
    switch (this.type) {
      case "comma":
      case "doc-start":
      case "doc-end":
      case "flow-seq-end":
      case "flow-map-end":
      case "map-value-ind":
        yield* this.pop(), yield* this.step();
        break;
      case "newline":
        this.onKeyLine = !1;
      // fallthrough
      case "space":
      case "comment":
      default:
        t.end ? t.end.push(this.sourceToken) : t.end = [this.sourceToken], this.type === "newline" && (yield* this.pop());
    }
  }
}
function _2(e) {
  const t = e.prettyErrors !== !1;
  return { lineCounter: e.lineCounter || t && new fm() || null, prettyErrors: t };
}
function T2(e, t = {}) {
  const { lineCounter: n, prettyErrors: r } = _2(t), s = new kl(n?.addNewLine), i = new sm(t);
  let a = null;
  for (const o of i.compose(s.parse(e), !0, e.length))
    if (!a)
      a = o;
    else if (a.options.logLevel !== "silent") {
      a.errors.push(new ks(o.range.slice(0, 2), "MULTIPLE_DOCS", "Source contains multiple documents; please use YAML.parseAllDocuments()"));
      break;
    }
  return r && n && (a.errors.forEach(qh(e, n)), a.warnings.forEach(qh(e, n))), a;
}
function M2(e, t, n) {
  let r;
  const s = T2(e, n);
  if (!s)
    return null;
  if (s.warnings.forEach((i) => O1(s.options.logLevel, i)), s.errors.length > 0) {
    if (s.options.logLevel !== "silent")
      throw s.errors[0];
    s.errors = [];
  }
  return s.toJS(Object.assign({ reviver: r }, n));
}
function O2(e, t, n) {
  let r = null;
  if (Array.isArray(t) ? r = t : n === void 0 && t && (n = t), typeof n == "string" && (n = n.length), typeof n == "number") {
    const s = Math.round(n);
    n = s < 1 ? void 0 : s > 8 ? { indent: 8 } : { indent: s };
  }
  if (e === void 0) {
    const { keepUndefined: s } = n ?? t ?? {};
    if (!s)
      return;
  }
  return us(e) && !r ? e.toString(n) : new ti(e, r, n).toString(n);
}
var oo, Jh;
function R2() {
  if (Jh) return oo;
  Jh = 1;
  function e(s) {
    if (typeof s != "string")
      throw new TypeError("Path must be a string. Received " + JSON.stringify(s));
  }
  function t(s, i) {
    for (var a = "", o = 0, l = -1, u = 0, f, c = 0; c <= s.length; ++c) {
      if (c < s.length)
        f = s.charCodeAt(c);
      else {
        if (f === 47)
          break;
        f = 47;
      }
      if (f === 47) {
        if (!(l === c - 1 || u === 1)) if (l !== c - 1 && u === 2) {
          if (a.length < 2 || o !== 2 || a.charCodeAt(a.length - 1) !== 46 || a.charCodeAt(a.length - 2) !== 46) {
            if (a.length > 2) {
              var d = a.lastIndexOf("/");
              if (d !== a.length - 1) {
                d === -1 ? (a = "", o = 0) : (a = a.slice(0, d), o = a.length - 1 - a.lastIndexOf("/")), l = c, u = 0;
                continue;
              }
            } else if (a.length === 2 || a.length === 1) {
              a = "", o = 0, l = c, u = 0;
              continue;
            }
          }
          i && (a.length > 0 ? a += "/.." : a = "..", o = 2);
        } else
          a.length > 0 ? a += "/" + s.slice(l + 1, c) : a = s.slice(l + 1, c), o = c - l - 1;
        l = c, u = 0;
      } else f === 46 && u !== -1 ? ++u : u = -1;
    }
    return a;
  }
  function n(s, i) {
    var a = i.dir || i.root, o = i.base || (i.name || "") + (i.ext || "");
    return a ? a === i.root ? a + o : a + s + o : o;
  }
  var r = {
    // path.resolve([from ...], to)
    resolve: function() {
      for (var i = "", a = !1, o, l = arguments.length - 1; l >= -1 && !a; l--) {
        var u;
        l >= 0 ? u = arguments[l] : (o === void 0 && (o = process.cwd()), u = o), e(u), u.length !== 0 && (i = u + "/" + i, a = u.charCodeAt(0) === 47);
      }
      return i = t(i, !a), a ? i.length > 0 ? "/" + i : "/" : i.length > 0 ? i : ".";
    },
    normalize: function(i) {
      if (e(i), i.length === 0) return ".";
      var a = i.charCodeAt(0) === 47, o = i.charCodeAt(i.length - 1) === 47;
      return i = t(i, !a), i.length === 0 && !a && (i = "."), i.length > 0 && o && (i += "/"), a ? "/" + i : i;
    },
    isAbsolute: function(i) {
      return e(i), i.length > 0 && i.charCodeAt(0) === 47;
    },
    join: function() {
      if (arguments.length === 0)
        return ".";
      for (var i, a = 0; a < arguments.length; ++a) {
        var o = arguments[a];
        e(o), o.length > 0 && (i === void 0 ? i = o : i += "/" + o);
      }
      return i === void 0 ? "." : r.normalize(i);
    },
    relative: function(i, a) {
      if (e(i), e(a), i === a || (i = r.resolve(i), a = r.resolve(a), i === a)) return "";
      for (var o = 1; o < i.length && i.charCodeAt(o) === 47; ++o)
        ;
      for (var l = i.length, u = l - o, f = 1; f < a.length && a.charCodeAt(f) === 47; ++f)
        ;
      for (var c = a.length, d = c - f, v = u < d ? u : d, D = -1, S = 0; S <= v; ++S) {
        if (S === v) {
          if (d > v) {
            if (a.charCodeAt(f + S) === 47)
              return a.slice(f + S + 1);
            if (S === 0)
              return a.slice(f + S);
          } else u > v && (i.charCodeAt(o + S) === 47 ? D = S : S === 0 && (D = 0));
          break;
        }
        var x = i.charCodeAt(o + S), N = a.charCodeAt(f + S);
        if (x !== N)
          break;
        x === 47 && (D = S);
      }
      var k = "";
      for (S = o + D + 1; S <= l; ++S)
        (S === l || i.charCodeAt(S) === 47) && (k.length === 0 ? k += ".." : k += "/..");
      return k.length > 0 ? k + a.slice(f + D) : (f += D, a.charCodeAt(f) === 47 && ++f, a.slice(f));
    },
    _makeLong: function(i) {
      return i;
    },
    dirname: function(i) {
      if (e(i), i.length === 0) return ".";
      for (var a = i.charCodeAt(0), o = a === 47, l = -1, u = !0, f = i.length - 1; f >= 1; --f)
        if (a = i.charCodeAt(f), a === 47) {
          if (!u) {
            l = f;
            break;
          }
        } else
          u = !1;
      return l === -1 ? o ? "/" : "." : o && l === 1 ? "//" : i.slice(0, l);
    },
    basename: function(i, a) {
      if (a !== void 0 && typeof a != "string") throw new TypeError('"ext" argument must be a string');
      e(i);
      var o = 0, l = -1, u = !0, f;
      if (a !== void 0 && a.length > 0 && a.length <= i.length) {
        if (a.length === i.length && a === i) return "";
        var c = a.length - 1, d = -1;
        for (f = i.length - 1; f >= 0; --f) {
          var v = i.charCodeAt(f);
          if (v === 47) {
            if (!u) {
              o = f + 1;
              break;
            }
          } else
            d === -1 && (u = !1, d = f + 1), c >= 0 && (v === a.charCodeAt(c) ? --c === -1 && (l = f) : (c = -1, l = d));
        }
        return o === l ? l = d : l === -1 && (l = i.length), i.slice(o, l);
      } else {
        for (f = i.length - 1; f >= 0; --f)
          if (i.charCodeAt(f) === 47) {
            if (!u) {
              o = f + 1;
              break;
            }
          } else l === -1 && (u = !1, l = f + 1);
        return l === -1 ? "" : i.slice(o, l);
      }
    },
    extname: function(i) {
      e(i);
      for (var a = -1, o = 0, l = -1, u = !0, f = 0, c = i.length - 1; c >= 0; --c) {
        var d = i.charCodeAt(c);
        if (d === 47) {
          if (!u) {
            o = c + 1;
            break;
          }
          continue;
        }
        l === -1 && (u = !1, l = c + 1), d === 46 ? a === -1 ? a = c : f !== 1 && (f = 1) : a !== -1 && (f = -1);
      }
      return a === -1 || l === -1 || // We saw a non-dot character immediately before the dot
      f === 0 || // The (right-most) trimmed path component is exactly '..'
      f === 1 && a === l - 1 && a === o + 1 ? "" : i.slice(a, l);
    },
    format: function(i) {
      if (i === null || typeof i != "object")
        throw new TypeError('The "pathObject" argument must be of type Object. Received type ' + typeof i);
      return n("/", i);
    },
    parse: function(i) {
      e(i);
      var a = { root: "", dir: "", base: "", ext: "", name: "" };
      if (i.length === 0) return a;
      var o = i.charCodeAt(0), l = o === 47, u;
      l ? (a.root = "/", u = 1) : u = 0;
      for (var f = -1, c = 0, d = -1, v = !0, D = i.length - 1, S = 0; D >= u; --D) {
        if (o = i.charCodeAt(D), o === 47) {
          if (!v) {
            c = D + 1;
            break;
          }
          continue;
        }
        d === -1 && (v = !1, d = D + 1), o === 46 ? f === -1 ? f = D : S !== 1 && (S = 1) : f !== -1 && (S = -1);
      }
      return f === -1 || d === -1 || // We saw a non-dot character immediately before the dot
      S === 0 || // The (right-most) trimmed path component is exactly '..'
      S === 1 && f === d - 1 && f === c + 1 ? d !== -1 && (c === 0 && l ? a.base = a.name = i.slice(1, d) : a.base = a.name = i.slice(c, d)) : (c === 0 && l ? (a.name = i.slice(1, f), a.base = i.slice(1, d)) : (a.name = i.slice(c, f), a.base = i.slice(c, d)), a.ext = i.slice(f, d)), c > 0 ? a.dir = i.slice(0, c - 1) : l && (a.dir = "/"), a;
    },
    sep: "/",
    delimiter: ":",
    win32: null,
    posix: null
  };
  return r.posix = r, oo = r, oo;
}
var nr = R2(), P2 = Object.create, Ma = Object.defineProperty, I2 = Object.getOwnPropertyDescriptor, $2 = Object.getOwnPropertyNames, B2 = Object.getPrototypeOf, V2 = Object.prototype.hasOwnProperty, dm = (e) => {
  throw TypeError(e);
}, j2 = (e, t, n) => t in e ? Ma(e, t, { enumerable: !0, configurable: !0, writable: !0, value: n }) : e[t] = n, pn = (e, t) => () => (t || e((t = { exports: {} }).exports, t), t.exports), mm = (e, t) => {
  for (var n in t) Ma(e, n, { get: t[n], enumerable: !0 });
}, U2 = (e, t, n, r) => {
  if (t && typeof t == "object" || typeof t == "function") for (let s of $2(t)) !V2.call(e, s) && s !== n && Ma(e, s, { get: () => t[s], enumerable: !(r = I2(t, s)) || r.enumerable });
  return e;
}, Su = (e, t, n) => (n = e != null ? P2(B2(e)) : {}, U2(Ma(n, "default", { value: e, enumerable: !0 }), e)), Qh = (e, t, n) => j2(e, typeof t != "symbol" ? t + "" : t, n), Eu = (e, t, n) => t.has(e) || dm("Cannot " + n), Ps = (e, t, n) => (Eu(e, t, "read from private field"), n ? n.call(e) : t.get(e)), lo = (e, t, n) => t.has(e) ? dm("Cannot add the same private member more than once") : t instanceof WeakSet ? t.add(e) : t.set(e, n), pm = (e, t, n, r) => (Eu(e, t, "write to private field"), t.set(e, n), n), ua = (e, t, n) => (Eu(e, t, "access private method"), n), fr = pn((e) => {
  var t = { ANCHOR: "&", COMMENT: "#", TAG: "!", DIRECTIVES_END: "-", DOCUMENT_END: "." }, n = { ALIAS: "ALIAS", BLANK_LINE: "BLANK_LINE", BLOCK_FOLDED: "BLOCK_FOLDED", BLOCK_LITERAL: "BLOCK_LITERAL", COMMENT: "COMMENT", DIRECTIVE: "DIRECTIVE", DOCUMENT: "DOCUMENT", FLOW_MAP: "FLOW_MAP", FLOW_SEQ: "FLOW_SEQ", MAP: "MAP", MAP_KEY: "MAP_KEY", MAP_VALUE: "MAP_VALUE", PLAIN: "PLAIN", QUOTE_DOUBLE: "QUOTE_DOUBLE", QUOTE_SINGLE: "QUOTE_SINGLE", SEQ: "SEQ", SEQ_ITEM: "SEQ_ITEM" }, r = "tag:yaml.org,2002:", s = { MAP: "tag:yaml.org,2002:map", SEQ: "tag:yaml.org,2002:seq", STR: "tag:yaml.org,2002:str" };
  function i(y) {
    let b = [0], h = y.indexOf(`
`);
    for (; h !== -1; ) h += 1, b.push(h), h = y.indexOf(`
`, h);
    return b;
  }
  function a(y) {
    let b, h;
    return typeof y == "string" ? (b = i(y), h = y) : (Array.isArray(y) && (y = y[0]), y && y.context && (y.lineStarts || (y.lineStarts = i(y.context.src)), b = y.lineStarts, h = y.context.src)), { lineStarts: b, src: h };
  }
  function o(y, b) {
    if (typeof y != "number" || y < 0) return null;
    let { lineStarts: h, src: m } = a(b);
    if (!h || !m || y > m.length) return null;
    for (let E = 0; E < h.length; ++E) {
      let w = h[E];
      if (y < w) return { line: E, col: y - h[E - 1] + 1 };
      if (y === w) return { line: E + 1, col: 1 };
    }
    let p = h.length;
    return { line: p, col: y - h[p - 1] + 1 };
  }
  function l(y, b) {
    let { lineStarts: h, src: m } = a(b);
    if (!h || !(y >= 1) || y > h.length) return null;
    let p = h[y - 1], E = h[y];
    for (; E && E > p && m[E - 1] === `
`; ) --E;
    return m.slice(p, E);
  }
  function u({ start: y, end: b }, h, m = 80) {
    let p = l(y.line, h);
    if (!p) return null;
    let { col: E } = y;
    if (p.length > m) if (E <= m - 10) p = p.substr(0, m - 1) + "…";
    else {
      let _ = Math.round(m / 2);
      p.length > E + _ && (p = p.substr(0, E + _ - 1) + "…"), E -= p.length - m, p = "…" + p.substr(1 - m);
    }
    let w = 1, L = "";
    b && (b.line === y.line && E + (b.col - y.col) <= m + 1 ? w = b.col - y.col : (w = Math.min(p.length + 1, m) - E, L = "…"));
    let C = E > 1 ? " ".repeat(E - 1) : "", A = "^".repeat(w);
    return `${p}
${C}${A}${L}`;
  }
  var f = class gm {
    static copy(b) {
      return new gm(b.start, b.end);
    }
    constructor(b, h) {
      this.start = b, this.end = h || b;
    }
    isEmpty() {
      return typeof this.start != "number" || !this.end || this.end <= this.start;
    }
    setOrigRange(b, h) {
      let { start: m, end: p } = this;
      if (b.length === 0 || p <= b[0]) return this.origStart = m, this.origEnd = p, h;
      let E = h;
      for (; E < b.length && !(b[E] > m); ) ++E;
      this.origStart = m + E;
      let w = E;
      for (; E < b.length && !(b[E] >= p); ) ++E;
      return this.origEnd = p + E, w;
    }
  }, c = class sn {
    static addStringTerminator(b, h, m) {
      if (m[m.length - 1] === `
`) return m;
      let p = sn.endOfWhiteSpace(b, h);
      return p >= b.length || b[p] === `
` ? m + `
` : m;
    }
    static atDocumentBoundary(b, h, m) {
      let p = b[h];
      if (!p) return !0;
      let E = b[h - 1];
      if (E && E !== `
`) return !1;
      if (m) {
        if (p !== m) return !1;
      } else if (p !== t.DIRECTIVES_END && p !== t.DOCUMENT_END) return !1;
      let w = b[h + 1], L = b[h + 2];
      if (w !== p || L !== p) return !1;
      let C = b[h + 3];
      return !C || C === `
` || C === "	" || C === " ";
    }
    static endOfIdentifier(b, h) {
      let m = b[h], p = m === "<", E = p ? [`
`, "	", " ", ">"] : [`
`, "	", " ", "[", "]", "{", "}", ","];
      for (; m && E.indexOf(m) === -1; ) m = b[h += 1];
      return p && m === ">" && (h += 1), h;
    }
    static endOfIndent(b, h) {
      let m = b[h];
      for (; m === " "; ) m = b[h += 1];
      return h;
    }
    static endOfLine(b, h) {
      let m = b[h];
      for (; m && m !== `
`; ) m = b[h += 1];
      return h;
    }
    static endOfWhiteSpace(b, h) {
      let m = b[h];
      for (; m === "	" || m === " "; ) m = b[h += 1];
      return h;
    }
    static startOfLine(b, h) {
      let m = b[h - 1];
      if (m === `
`) return h;
      for (; m && m !== `
`; ) m = b[h -= 1];
      return h + 1;
    }
    static endOfBlockIndent(b, h, m) {
      let p = sn.endOfIndent(b, m);
      if (p > m + h) return p;
      {
        let E = sn.endOfWhiteSpace(b, p), w = b[E];
        if (!w || w === `
`) return E;
      }
      return null;
    }
    static atBlank(b, h, m) {
      let p = b[h];
      return p === `
` || p === "	" || p === " " || m && !p;
    }
    static nextNodeIsIndented(b, h, m) {
      return !b || h < 0 ? !1 : h > 0 ? !0 : m && b === "-";
    }
    static normalizeOffset(b, h) {
      let m = b[h];
      return m ? m !== `
` && b[h - 1] === `
` ? h - 1 : sn.endOfWhiteSpace(b, h) : h;
    }
    static foldNewline(b, h, m) {
      let p = 0, E = !1, w = "", L = b[h + 1];
      for (; L === " " || L === "	" || L === `
`; ) {
        switch (L) {
          case `
`:
            p = 0, h += 1, w += `
`;
            break;
          case "	":
            p <= m && (E = !0), h = sn.endOfWhiteSpace(b, h + 2) - 1;
            break;
          case " ":
            p += 1, h += 1;
            break;
        }
        L = b[h + 1];
      }
      return w || (w = " "), L && p <= m && (E = !0), { fold: w, offset: h, error: E };
    }
    constructor(b, h, m) {
      Object.defineProperty(this, "context", { value: m || null, writable: !0 }), this.error = null, this.range = null, this.valueRange = null, this.props = h || [], this.type = b, this.value = null;
    }
    getPropValue(b, h, m) {
      if (!this.context) return null;
      let { src: p } = this.context, E = this.props[b];
      return E && p[E.start] === h ? p.slice(E.start + (m ? 1 : 0), E.end) : null;
    }
    get anchor() {
      for (let b = 0; b < this.props.length; ++b) {
        let h = this.getPropValue(b, t.ANCHOR, !0);
        if (h != null) return h;
      }
      return null;
    }
    get comment() {
      let b = [];
      for (let h = 0; h < this.props.length; ++h) {
        let m = this.getPropValue(h, t.COMMENT, !0);
        m != null && b.push(m);
      }
      return b.length > 0 ? b.join(`
`) : null;
    }
    commentHasRequiredWhitespace(b) {
      let { src: h } = this.context;
      if (this.header && b === this.header.end || !this.valueRange) return !1;
      let { end: m } = this.valueRange;
      return b !== m || sn.atBlank(h, m - 1);
    }
    get hasComment() {
      if (this.context) {
        let { src: b } = this.context;
        for (let h = 0; h < this.props.length; ++h) if (b[this.props[h].start] === t.COMMENT) return !0;
      }
      return !1;
    }
    get hasProps() {
      if (this.context) {
        let { src: b } = this.context;
        for (let h = 0; h < this.props.length; ++h) if (b[this.props[h].start] !== t.COMMENT) return !0;
      }
      return !1;
    }
    get includesTrailingLines() {
      return !1;
    }
    get jsonLike() {
      return [n.FLOW_MAP, n.FLOW_SEQ, n.QUOTE_DOUBLE, n.QUOTE_SINGLE].indexOf(this.type) !== -1;
    }
    get rangeAsLinePos() {
      if (!this.range || !this.context) return;
      let b = o(this.range.start, this.context.root);
      if (!b) return;
      let h = o(this.range.end, this.context.root);
      return { start: b, end: h };
    }
    get rawValue() {
      if (!this.valueRange || !this.context) return null;
      let { start: b, end: h } = this.valueRange;
      return this.context.src.slice(b, h);
    }
    get tag() {
      for (let b = 0; b < this.props.length; ++b) {
        let h = this.getPropValue(b, t.TAG, !1);
        if (h != null) {
          if (h[1] === "<") return { verbatim: h.slice(2, -1) };
          {
            let [m, p, E] = h.match(/^(.*!)([^!]*)$/);
            return { handle: p, suffix: E };
          }
        }
      }
      return null;
    }
    get valueRangeContainsNewline() {
      if (!this.valueRange || !this.context) return !1;
      let { start: b, end: h } = this.valueRange, { src: m } = this.context;
      for (let p = b; p < h; ++p) if (m[p] === `
`) return !0;
      return !1;
    }
    parseComment(b) {
      let { src: h } = this.context;
      if (h[b] === t.COMMENT) {
        let m = sn.endOfLine(h, b + 1), p = new f(b, m);
        return this.props.push(p), m;
      }
      return b;
    }
    setOrigRanges(b, h) {
      return this.range && (h = this.range.setOrigRange(b, h)), this.valueRange && this.valueRange.setOrigRange(b, h), this.props.forEach((m) => m.setOrigRange(b, h)), h;
    }
    toString() {
      let { context: { src: b }, range: h, value: m } = this;
      if (m != null) return m;
      let p = b.slice(h.start, h.end);
      return sn.addStringTerminator(b, h.end, p);
    }
  }, d = class extends Error {
    constructor(y, b, h) {
      if (!h || !(b instanceof c)) throw new Error(`Invalid arguments for new ${y}`);
      super(), this.name = y, this.message = h, this.source = b;
    }
    makePretty() {
      if (!this.source) return;
      this.nodeType = this.source.type;
      let y = this.source.context && this.source.context.root;
      if (typeof this.offset == "number") {
        this.range = new f(this.offset, this.offset + 1);
        let b = y && o(this.offset, y);
        if (b) {
          let h = { line: b.line, col: b.col + 1 };
          this.linePos = { start: b, end: h };
        }
        delete this.offset;
      } else this.range = this.source.range, this.linePos = this.source.rangeAsLinePos;
      if (this.linePos) {
        let { line: b, col: h } = this.linePos.start;
        this.message += ` at line ${b}, column ${h}`;
        let m = y && u(this.linePos, y);
        m && (this.message += `:

${m}
`);
      }
      delete this.source;
    }
  }, v = class extends d {
    constructor(y, b) {
      super("YAMLReferenceError", y, b);
    }
  }, D = class extends d {
    constructor(y, b) {
      super("YAMLSemanticError", y, b);
    }
  }, S = class extends d {
    constructor(y, b) {
      super("YAMLSyntaxError", y, b);
    }
  }, x = class extends d {
    constructor(y, b) {
      super("YAMLWarning", y, b);
    }
  };
  function N(y, b, h) {
    return b in y ? Object.defineProperty(y, b, { value: h, enumerable: !0, configurable: !0, writable: !0 }) : y[b] = h, y;
  }
  var k = class Cl extends c {
    static endOfLine(b, h, m) {
      let p = b[h], E = h;
      for (; p && p !== `
` && !(m && (p === "[" || p === "]" || p === "{" || p === "}" || p === ",")); ) {
        let w = b[E + 1];
        if (p === ":" && (!w || w === `
` || w === "	" || w === " " || m && w === ",") || (p === " " || p === "	") && w === "#") break;
        E += 1, p = w;
      }
      return E;
    }
    get strValue() {
      if (!this.valueRange || !this.context) return null;
      let { start: b, end: h } = this.valueRange, { src: m } = this.context, p = m[h - 1];
      for (; b < h && (p === `
` || p === "	" || p === " "); ) p = m[--h - 1];
      let E = "";
      for (let L = b; L < h; ++L) {
        let C = m[L];
        if (C === `
`) {
          let { fold: A, offset: _ } = c.foldNewline(m, L, -1);
          E += A, L = _;
        } else if (C === " " || C === "	") {
          let A = L, _ = m[L + 1];
          for (; L < h && (_ === " " || _ === "	"); ) L += 1, _ = m[L + 1];
          _ !== `
` && (E += L > A ? m.slice(A, L + 1) : C);
        } else E += C;
      }
      let w = m[b];
      switch (w) {
        case "	": {
          let L = "Plain value cannot start with a tab character";
          return { errors: [new D(this, L)], str: E };
        }
        case "@":
        case "`": {
          let L = `Plain value cannot start with reserved character ${w}`;
          return { errors: [new D(this, L)], str: E };
        }
        default:
          return E;
      }
    }
    parseBlockValue(b) {
      let { indent: h, inFlow: m, src: p } = this.context, E = b, w = b;
      for (let L = p[E]; L === `
` && !c.atDocumentBoundary(p, E + 1); L = p[E]) {
        let C = c.endOfBlockIndent(p, h, E + 1);
        if (C === null || p[C] === "#") break;
        p[C] === `
` ? E = C : (w = Cl.endOfLine(p, C, m), E = w);
      }
      return this.valueRange.isEmpty() && (this.valueRange.start = b), this.valueRange.end = w, w;
    }
    parse(b, h) {
      this.context = b;
      let { inFlow: m, src: p } = b, E = h, w = p[E];
      return w && w !== "#" && w !== `
` && (E = Cl.endOfLine(p, h, m)), this.valueRange = new f(h, E), E = c.endOfWhiteSpace(p, E), E = this.parseComment(E), (!this.hasComment || this.valueRange.isEmpty()) && (E = this.parseBlockValue(E)), E;
    }
  };
  e.Char = t, e.Node = c, e.PlainValue = k, e.Range = f, e.Type = n, e.YAMLError = d, e.YAMLReferenceError = v, e.YAMLSemanticError = D, e.YAMLSyntaxError = S, e.YAMLWarning = x, e._defineProperty = N, e.defaultTagPrefix = r, e.defaultTags = s;
}), q2 = pn((e) => {
  var t = fr(), n = class extends t.Node {
    constructor() {
      super(t.Type.BLANK_LINE);
    }
    get includesTrailingLines() {
      return !0;
    }
    parse(k, y) {
      return this.context = k, this.range = new t.Range(y, y + 1), y + 1;
    }
  }, r = class extends t.Node {
    constructor(k, y) {
      super(k, y), this.node = null;
    }
    get includesTrailingLines() {
      return !!this.node && this.node.includesTrailingLines;
    }
    parse(k, y) {
      this.context = k;
      let { parseNode: b, src: h } = k, { atLineStart: m, lineStart: p } = k;
      !m && this.type === t.Type.SEQ_ITEM && (this.error = new t.YAMLSemanticError(this, "Sequence items must not have preceding content on the same line"));
      let E = m ? y - p : k.indent, w = t.Node.endOfWhiteSpace(h, y + 1), L = h[w], C = L === "#", A = [], _ = null;
      for (; L === `
` || L === "#"; ) {
        if (L === "#") {
          let T = t.Node.endOfLine(h, w + 1);
          A.push(new t.Range(w, T)), w = T;
        } else {
          m = !0, p = w + 1;
          let T = t.Node.endOfWhiteSpace(h, p);
          h[T] === `
` && A.length === 0 && (_ = new n(), p = _.parse({ src: h }, p)), w = t.Node.endOfIndent(h, p);
        }
        L = h[w];
      }
      if (t.Node.nextNodeIsIndented(L, w - (p + E), this.type !== t.Type.SEQ_ITEM) ? this.node = b({ atLineStart: m, inCollection: !1, indent: E, lineStart: p, parent: this }, w) : L && p > y + 1 && (w = p - 1), this.node) {
        if (_) {
          let T = k.parent.items || k.parent.contents;
          T && T.push(_);
        }
        A.length && Array.prototype.push.apply(this.props, A), w = this.node.range.end;
      } else if (C) {
        let T = A[0];
        this.props.push(T), w = T.end;
      } else w = t.Node.endOfLine(h, y + 1);
      let O = this.node ? this.node.valueRange.end : w;
      return this.valueRange = new t.Range(y, O), w;
    }
    setOrigRanges(k, y) {
      return y = super.setOrigRanges(k, y), this.node ? this.node.setOrigRanges(k, y) : y;
    }
    toString() {
      let { context: { src: k }, node: y, range: b, value: h } = this;
      if (h != null) return h;
      let m = y ? k.slice(b.start, y.range.start) + String(y) : k.slice(b.start, b.end);
      return t.Node.addStringTerminator(k, b.end, m);
    }
  }, s = class extends t.Node {
    constructor() {
      super(t.Type.COMMENT);
    }
    parse(k, y) {
      this.context = k;
      let b = this.parseComment(y);
      return this.range = new t.Range(y, b), b;
    }
  };
  function i(k) {
    let y = k;
    for (; y instanceof r; ) y = y.node;
    if (!(y instanceof a)) return null;
    let b = y.items.length, h = -1;
    for (let E = b - 1; E >= 0; --E) {
      let w = y.items[E];
      if (w.type === t.Type.COMMENT) {
        let { indent: L, lineStart: C } = w.context;
        if (L > 0 && w.range.start >= C + L) break;
        h = E;
      } else if (w.type === t.Type.BLANK_LINE) h = E;
      else break;
    }
    if (h === -1) return null;
    let m = y.items.splice(h, b - h), p = m[0].range.start;
    for (; y.range.end = p, y.valueRange && y.valueRange.end > p && (y.valueRange.end = p), y !== k; ) y = y.context.parent;
    return m;
  }
  var a = class Fl extends t.Node {
    static nextContentHasIndent(y, b, h) {
      let m = t.Node.endOfLine(y, b) + 1;
      b = t.Node.endOfWhiteSpace(y, m);
      let p = y[b];
      return p ? b >= m + h ? !0 : p !== "#" && p !== `
` ? !1 : Fl.nextContentHasIndent(y, b, h) : !1;
    }
    constructor(y) {
      super(y.type === t.Type.SEQ_ITEM ? t.Type.SEQ : t.Type.MAP);
      for (let h = y.props.length - 1; h >= 0; --h) if (y.props[h].start < y.context.lineStart) {
        this.props = y.props.slice(0, h + 1), y.props = y.props.slice(h + 1);
        let m = y.props[0] || y.valueRange;
        y.range.start = m.start;
        break;
      }
      this.items = [y];
      let b = i(y);
      b && Array.prototype.push.apply(this.items, b);
    }
    get includesTrailingLines() {
      return this.items.length > 0;
    }
    parse(y, b) {
      this.context = y;
      let { parseNode: h, src: m } = y, p = t.Node.startOfLine(m, b), E = this.items[0];
      E.context.parent = this, this.valueRange = t.Range.copy(E.valueRange);
      let w = E.range.start - E.context.lineStart, L = b;
      L = t.Node.normalizeOffset(m, L);
      let C = m[L], A = t.Node.endOfWhiteSpace(m, p) === L, _ = !1;
      for (; C; ) {
        for (; C === `
` || C === "#"; ) {
          if (A && C === `
` && !_) {
            let P = new n();
            if (L = P.parse({ src: m }, L), this.valueRange.end = L, L >= m.length) {
              C = null;
              break;
            }
            this.items.push(P), L -= 1;
          } else if (C === "#") {
            if (L < p + w && !Fl.nextContentHasIndent(m, L, w)) return L;
            let P = new s();
            if (L = P.parse({ indent: w, lineStart: p, src: m }, L), this.items.push(P), this.valueRange.end = L, L >= m.length) {
              C = null;
              break;
            }
          }
          if (p = L + 1, L = t.Node.endOfIndent(m, p), t.Node.atBlank(m, L)) {
            let P = t.Node.endOfWhiteSpace(m, L), V = m[P];
            (!V || V === `
` || V === "#") && (L = P);
          }
          C = m[L], A = !0;
        }
        if (!C) break;
        if (L !== p + w && (A || C !== ":")) {
          if (L < p + w) {
            p > b && (L = p);
            break;
          } else if (!this.error) {
            let P = "All collection items must start at the same column";
            this.error = new t.YAMLSyntaxError(this, P);
          }
        }
        if (E.type === t.Type.SEQ_ITEM) {
          if (C !== "-") {
            p > b && (L = p);
            break;
          }
        } else if (C === "-" && !this.error) {
          let P = m[L + 1];
          if (!P || P === `
` || P === "	" || P === " ") {
            let V = "A collection cannot be both a mapping and a sequence";
            this.error = new t.YAMLSyntaxError(this, V);
          }
        }
        let O = h({ atLineStart: A, inCollection: !0, indent: w, lineStart: p, parent: this }, L);
        if (!O) return L;
        if (this.items.push(O), this.valueRange.end = O.valueRange.end, L = t.Node.normalizeOffset(m, O.range.end), C = m[L], A = !1, _ = O.includesTrailingLines, C) {
          let P = L - 1, V = m[P];
          for (; V === " " || V === "	"; ) V = m[--P];
          V === `
` && (p = P + 1, A = !0);
        }
        let T = i(O);
        T && Array.prototype.push.apply(this.items, T);
      }
      return L;
    }
    setOrigRanges(y, b) {
      return b = super.setOrigRanges(y, b), this.items.forEach((h) => {
        b = h.setOrigRanges(y, b);
      }), b;
    }
    toString() {
      let { context: { src: y }, items: b, range: h, value: m } = this;
      if (m != null) return m;
      let p = y.slice(h.start, b[0].range.start) + String(b[0]);
      for (let E = 1; E < b.length; ++E) {
        let w = b[E], { atLineStart: L, indent: C } = w.context;
        if (L) for (let A = 0; A < C; ++A) p += " ";
        p += String(w);
      }
      return t.Node.addStringTerminator(y, h.end, p);
    }
  }, o = class extends t.Node {
    constructor() {
      super(t.Type.DIRECTIVE), this.name = null;
    }
    get parameters() {
      let k = this.rawValue;
      return k ? k.trim().split(/[ \t]+/) : [];
    }
    parseName(k) {
      let { src: y } = this.context, b = k, h = y[b];
      for (; h && h !== `
` && h !== "	" && h !== " "; ) h = y[b += 1];
      return this.name = y.slice(k, b), b;
    }
    parseParameters(k) {
      let { src: y } = this.context, b = k, h = y[b];
      for (; h && h !== `
` && h !== "#"; ) h = y[b += 1];
      return this.valueRange = new t.Range(k, b), b;
    }
    parse(k, y) {
      this.context = k;
      let b = this.parseName(y + 1);
      return b = this.parseParameters(b), b = this.parseComment(b), this.range = new t.Range(y, b), b;
    }
  }, l = class _l extends t.Node {
    static startCommentOrEndBlankLine(y, b) {
      let h = t.Node.endOfWhiteSpace(y, b), m = y[h];
      return m === "#" || m === `
` ? h : b;
    }
    constructor() {
      super(t.Type.DOCUMENT), this.directives = null, this.contents = null, this.directivesEndMarker = null, this.documentEndMarker = null;
    }
    parseDirectives(y) {
      let { src: b } = this.context;
      this.directives = [];
      let h = !0, m = !1, p = y;
      for (; !t.Node.atDocumentBoundary(b, p, t.Char.DIRECTIVES_END); ) switch (p = _l.startCommentOrEndBlankLine(b, p), b[p]) {
        case `
`:
          if (h) {
            let E = new n();
            p = E.parse({ src: b }, p), p < b.length && this.directives.push(E);
          } else p += 1, h = !0;
          break;
        case "#":
          {
            let E = new s();
            p = E.parse({ src: b }, p), this.directives.push(E), h = !1;
          }
          break;
        case "%":
          {
            let E = new o();
            p = E.parse({ parent: this, src: b }, p), this.directives.push(E), m = !0, h = !1;
          }
          break;
        default:
          return m ? this.error = new t.YAMLSemanticError(this, "Missing directives-end indicator line") : this.directives.length > 0 && (this.contents = this.directives, this.directives = []), p;
      }
      return b[p] ? (this.directivesEndMarker = new t.Range(p, p + 3), p + 3) : (m ? this.error = new t.YAMLSemanticError(this, "Missing directives-end indicator line") : this.directives.length > 0 && (this.contents = this.directives, this.directives = []), p);
    }
    parseContents(y) {
      let { parseNode: b, src: h } = this.context;
      this.contents || (this.contents = []);
      let m = y;
      for (; h[m - 1] === "-"; ) m -= 1;
      let p = t.Node.endOfWhiteSpace(h, y), E = m === y;
      for (this.valueRange = new t.Range(p); !t.Node.atDocumentBoundary(h, p, t.Char.DOCUMENT_END); ) {
        switch (h[p]) {
          case `
`:
            if (E) {
              let w = new n();
              p = w.parse({ src: h }, p), p < h.length && this.contents.push(w);
            } else p += 1, E = !0;
            m = p;
            break;
          case "#":
            {
              let w = new s();
              p = w.parse({ src: h }, p), this.contents.push(w), E = !1;
            }
            break;
          default: {
            let w = t.Node.endOfIndent(h, p), L = b({ atLineStart: E, indent: -1, inFlow: !1, inCollection: !1, lineStart: m, parent: this }, w);
            if (!L) return this.valueRange.end = w;
            this.contents.push(L), p = L.range.end, E = !1;
            let C = i(L);
            C && Array.prototype.push.apply(this.contents, C);
          }
        }
        p = _l.startCommentOrEndBlankLine(h, p);
      }
      if (this.valueRange.end = p, h[p] && (this.documentEndMarker = new t.Range(p, p + 3), p += 3, h[p])) {
        if (p = t.Node.endOfWhiteSpace(h, p), h[p] === "#") {
          let w = new s();
          p = w.parse({ src: h }, p), this.contents.push(w);
        }
        switch (h[p]) {
          case `
`:
            p += 1;
            break;
          case void 0:
            break;
          default:
            this.error = new t.YAMLSyntaxError(this, "Document end marker line cannot have a non-comment suffix");
        }
      }
      return p;
    }
    parse(y, b) {
      y.root = this, this.context = y;
      let { src: h } = y, m = h.charCodeAt(b) === 65279 ? b + 1 : b;
      return m = this.parseDirectives(m), m = this.parseContents(m), m;
    }
    setOrigRanges(y, b) {
      return b = super.setOrigRanges(y, b), this.directives.forEach((h) => {
        b = h.setOrigRanges(y, b);
      }), this.directivesEndMarker && (b = this.directivesEndMarker.setOrigRange(y, b)), this.contents.forEach((h) => {
        b = h.setOrigRanges(y, b);
      }), this.documentEndMarker && (b = this.documentEndMarker.setOrigRange(y, b)), b;
    }
    toString() {
      let { contents: y, directives: b, value: h } = this;
      if (h != null) return h;
      let m = b.join("");
      return y.length > 0 && ((b.length > 0 || y[0].type === t.Type.COMMENT) && (m += `---
`), m += y.join("")), m[m.length - 1] !== `
` && (m += `
`), m;
    }
  }, u = class extends t.Node {
    parse(k, y) {
      this.context = k;
      let { src: b } = k, h = t.Node.endOfIdentifier(b, y + 1);
      return this.valueRange = new t.Range(y + 1, h), h = t.Node.endOfWhiteSpace(b, h), h = this.parseComment(h), h;
    }
  }, f = { CLIP: "CLIP", KEEP: "KEEP", STRIP: "STRIP" }, c = class extends t.Node {
    constructor(k, y) {
      super(k, y), this.blockIndent = null, this.chomping = f.CLIP, this.header = null;
    }
    get includesTrailingLines() {
      return this.chomping === f.KEEP;
    }
    get strValue() {
      if (!this.valueRange || !this.context) return null;
      let { start: k, end: y } = this.valueRange, { indent: b, src: h } = this.context;
      if (this.valueRange.isEmpty()) return "";
      let m = null, p = h[y - 1];
      for (; p === `
` || p === "	" || p === " "; ) {
        if (y -= 1, y <= k) {
          if (this.chomping === f.KEEP) break;
          return "";
        }
        p === `
` && (m = y), p = h[y - 1];
      }
      let E = y + 1;
      m && (this.chomping === f.KEEP ? (E = m, y = this.valueRange.end) : y = m);
      let w = b + this.blockIndent, L = this.type === t.Type.BLOCK_FOLDED, C = !0, A = "", _ = "", O = !1;
      for (let T = k; T < y; ++T) {
        for (let V = 0; V < w && h[T] === " "; ++V) T += 1;
        let P = h[T];
        if (P === `
`) _ === `
` ? A += `
` : _ = `
`;
        else {
          let V = t.Node.endOfLine(h, T), Y = h.slice(T, V);
          T = V, L && (P === " " || P === "	") && T < E ? (_ === " " ? _ = `
` : !O && !C && _ === `
` && (_ = `

`), A += _ + Y, _ = V < y && h[V] || "", O = !0) : (A += _ + Y, _ = L && T < E ? " " : `
`, O = !1), C && Y !== "" && (C = !1);
        }
      }
      return this.chomping === f.STRIP ? A : A + `
`;
    }
    parseBlockHeader(k) {
      let { src: y } = this.context, b = k + 1, h = "";
      for (; ; ) {
        let m = y[b];
        switch (m) {
          case "-":
            this.chomping = f.STRIP;
            break;
          case "+":
            this.chomping = f.KEEP;
            break;
          case "0":
          case "1":
          case "2":
          case "3":
          case "4":
          case "5":
          case "6":
          case "7":
          case "8":
          case "9":
            h += m;
            break;
          default:
            return this.blockIndent = Number(h) || null, this.header = new t.Range(k, b), b;
        }
        b += 1;
      }
    }
    parseBlockValue(k) {
      let { indent: y, src: b } = this.context, h = !!this.blockIndent, m = k, p = k, E = 1;
      for (let w = b[m]; w === `
` && (m += 1, !t.Node.atDocumentBoundary(b, m)); w = b[m]) {
        let L = t.Node.endOfBlockIndent(b, y, m);
        if (L === null) break;
        let C = b[L], A = L - (m + y);
        if (this.blockIndent) {
          if (C && C !== `
` && A < this.blockIndent) {
            if (b[L] === "#") break;
            if (!this.error) {
              let _ = `Block scalars must not be less indented than their ${h ? "explicit indentation indicator" : "first line"}`;
              this.error = new t.YAMLSemanticError(this, _);
            }
          }
        } else if (b[L] !== `
`) {
          if (A < E) {
            let _ = "Block scalars with more-indented leading empty lines must use an explicit indentation indicator";
            this.error = new t.YAMLSemanticError(this, _);
          }
          this.blockIndent = A;
        } else A > E && (E = A);
        b[L] === `
` ? m = L : m = p = t.Node.endOfLine(b, L);
      }
      return this.chomping !== f.KEEP && (m = b[p] ? p + 1 : p), this.valueRange = new t.Range(k + 1, m), m;
    }
    parse(k, y) {
      this.context = k;
      let { src: b } = k, h = this.parseBlockHeader(y);
      return h = t.Node.endOfWhiteSpace(b, h), h = this.parseComment(h), h = this.parseBlockValue(h), h;
    }
    setOrigRanges(k, y) {
      return y = super.setOrigRanges(k, y), this.header ? this.header.setOrigRange(k, y) : y;
    }
  }, d = class extends t.Node {
    constructor(k, y) {
      super(k, y), this.items = null;
    }
    prevNodeIsJsonLike(k = this.items.length) {
      let y = this.items[k - 1];
      return !!y && (y.jsonLike || y.type === t.Type.COMMENT && this.prevNodeIsJsonLike(k - 1));
    }
    parse(k, y) {
      this.context = k;
      let { parseNode: b, src: h } = k, { indent: m, lineStart: p } = k, E = h[y];
      this.items = [{ char: E, offset: y }];
      let w = t.Node.endOfWhiteSpace(h, y + 1);
      for (E = h[w]; E && E !== "]" && E !== "}"; ) {
        switch (E) {
          case `
`:
            {
              p = w + 1;
              let L = t.Node.endOfWhiteSpace(h, p);
              if (h[L] === `
`) {
                let C = new n();
                p = C.parse({ src: h }, p), this.items.push(C);
              }
              if (w = t.Node.endOfIndent(h, p), w <= p + m && (E = h[w], w < p + m || E !== "]" && E !== "}")) {
                let C = "Insufficient indentation in flow collection";
                this.error = new t.YAMLSemanticError(this, C);
              }
            }
            break;
          case ",":
            this.items.push({ char: E, offset: w }), w += 1;
            break;
          case "#":
            {
              let L = new s();
              w = L.parse({ src: h }, w), this.items.push(L);
            }
            break;
          case "?":
          case ":": {
            let L = h[w + 1];
            if (L === `
` || L === "	" || L === " " || L === "," || E === ":" && this.prevNodeIsJsonLike()) {
              this.items.push({ char: E, offset: w }), w += 1;
              break;
            }
          }
          default: {
            let L = b({ atLineStart: !1, inCollection: !1, inFlow: !0, indent: -1, lineStart: p, parent: this }, w);
            if (!L) return this.valueRange = new t.Range(y, w), w;
            this.items.push(L), w = t.Node.normalizeOffset(h, L.range.end);
          }
        }
        w = t.Node.endOfWhiteSpace(h, w), E = h[w];
      }
      return this.valueRange = new t.Range(y, w + 1), E && (this.items.push({ char: E, offset: w }), w = t.Node.endOfWhiteSpace(h, w + 1), w = this.parseComment(w)), w;
    }
    setOrigRanges(k, y) {
      return y = super.setOrigRanges(k, y), this.items.forEach((b) => {
        if (b instanceof t.Node) y = b.setOrigRanges(k, y);
        else if (k.length === 0) b.origOffset = b.offset;
        else {
          let h = y;
          for (; h < k.length && !(k[h] > b.offset); ) ++h;
          b.origOffset = b.offset + h, y = h;
        }
      }), y;
    }
    toString() {
      let { context: { src: k }, items: y, range: b, value: h } = this;
      if (h != null) return h;
      let m = y.filter((w) => w instanceof t.Node), p = "", E = b.start;
      return m.forEach((w) => {
        let L = k.slice(E, w.range.start);
        E = w.range.end, p += L + String(w), p[p.length - 1] === `
` && k[E - 1] !== `
` && k[E] === `
` && (E += 1);
      }), p += k.slice(E, b.end), t.Node.addStringTerminator(k, b.end, p);
    }
  }, v = class ym extends t.Node {
    static endOfQuote(y, b) {
      let h = y[b];
      for (; h && h !== '"'; ) b += h === "\\" ? 2 : 1, h = y[b];
      return b + 1;
    }
    get strValue() {
      if (!this.valueRange || !this.context) return null;
      let y = [], { start: b, end: h } = this.valueRange, { indent: m, src: p } = this.context;
      p[h - 1] !== '"' && y.push(new t.YAMLSyntaxError(this, 'Missing closing "quote'));
      let E = "";
      for (let w = b + 1; w < h - 1; ++w) {
        let L = p[w];
        if (L === `
`) {
          t.Node.atDocumentBoundary(p, w + 1) && y.push(new t.YAMLSemanticError(this, "Document boundary indicators are not allowed within string values"));
          let { fold: C, offset: A, error: _ } = t.Node.foldNewline(p, w, m);
          E += C, w = A, _ && y.push(new t.YAMLSemanticError(this, "Multi-line double-quoted string needs to be sufficiently indented"));
        } else if (L === "\\") switch (w += 1, p[w]) {
          case "0":
            E += "\0";
            break;
          case "a":
            E += "\x07";
            break;
          case "b":
            E += "\b";
            break;
          case "e":
            E += "\x1B";
            break;
          case "f":
            E += "\f";
            break;
          case "n":
            E += `
`;
            break;
          case "r":
            E += "\r";
            break;
          case "t":
            E += "	";
            break;
          case "v":
            E += "\v";
            break;
          case "N":
            E += "";
            break;
          case "_":
            E += " ";
            break;
          case "L":
            E += "\u2028";
            break;
          case "P":
            E += "\u2029";
            break;
          case " ":
            E += " ";
            break;
          case '"':
            E += '"';
            break;
          case "/":
            E += "/";
            break;
          case "\\":
            E += "\\";
            break;
          case "	":
            E += "	";
            break;
          case "x":
            E += this.parseCharCode(w + 1, 2, y), w += 2;
            break;
          case "u":
            E += this.parseCharCode(w + 1, 4, y), w += 4;
            break;
          case "U":
            E += this.parseCharCode(w + 1, 8, y), w += 8;
            break;
          case `
`:
            for (; p[w + 1] === " " || p[w + 1] === "	"; ) w += 1;
            break;
          default:
            y.push(new t.YAMLSyntaxError(this, `Invalid escape sequence ${p.substr(w - 1, 2)}`)), E += "\\" + p[w];
        }
        else if (L === " " || L === "	") {
          let C = w, A = p[w + 1];
          for (; A === " " || A === "	"; ) w += 1, A = p[w + 1];
          A !== `
` && (E += w > C ? p.slice(C, w + 1) : L);
        } else E += L;
      }
      return y.length > 0 ? { errors: y, str: E } : E;
    }
    parseCharCode(y, b, h) {
      let { src: m } = this.context, p = m.substr(y, b), E = p.length === b && /^[0-9a-fA-F]+$/.test(p) ? parseInt(p, 16) : NaN;
      return isNaN(E) ? (h.push(new t.YAMLSyntaxError(this, `Invalid escape sequence ${m.substr(y - 2, b + 2)}`)), m.substr(y - 2, b + 2)) : String.fromCodePoint(E);
    }
    parse(y, b) {
      this.context = y;
      let { src: h } = y, m = ym.endOfQuote(h, b + 1);
      return this.valueRange = new t.Range(b, m), m = t.Node.endOfWhiteSpace(h, m), m = this.parseComment(m), m;
    }
  }, D = class bm extends t.Node {
    static endOfQuote(y, b) {
      let h = y[b];
      for (; h; ) if (h === "'") {
        if (y[b + 1] !== "'") break;
        h = y[b += 2];
      } else h = y[b += 1];
      return b + 1;
    }
    get strValue() {
      if (!this.valueRange || !this.context) return null;
      let y = [], { start: b, end: h } = this.valueRange, { indent: m, src: p } = this.context;
      p[h - 1] !== "'" && y.push(new t.YAMLSyntaxError(this, "Missing closing 'quote"));
      let E = "";
      for (let w = b + 1; w < h - 1; ++w) {
        let L = p[w];
        if (L === `
`) {
          t.Node.atDocumentBoundary(p, w + 1) && y.push(new t.YAMLSemanticError(this, "Document boundary indicators are not allowed within string values"));
          let { fold: C, offset: A, error: _ } = t.Node.foldNewline(p, w, m);
          E += C, w = A, _ && y.push(new t.YAMLSemanticError(this, "Multi-line single-quoted string needs to be sufficiently indented"));
        } else if (L === "'") E += L, w += 1, p[w] !== "'" && y.push(new t.YAMLSyntaxError(this, "Unescaped single quote? This should not happen."));
        else if (L === " " || L === "	") {
          let C = w, A = p[w + 1];
          for (; A === " " || A === "	"; ) w += 1, A = p[w + 1];
          A !== `
` && (E += w > C ? p.slice(C, w + 1) : L);
        } else E += L;
      }
      return y.length > 0 ? { errors: y, str: E } : E;
    }
    parse(y, b) {
      this.context = y;
      let { src: h } = y, m = bm.endOfQuote(h, b + 1);
      return this.valueRange = new t.Range(b, m), m = t.Node.endOfWhiteSpace(h, m), m = this.parseComment(m), m;
    }
  };
  function S(k, y) {
    switch (k) {
      case t.Type.ALIAS:
        return new u(k, y);
      case t.Type.BLOCK_FOLDED:
      case t.Type.BLOCK_LITERAL:
        return new c(k, y);
      case t.Type.FLOW_MAP:
      case t.Type.FLOW_SEQ:
        return new d(k, y);
      case t.Type.MAP_KEY:
      case t.Type.MAP_VALUE:
      case t.Type.SEQ_ITEM:
        return new r(k, y);
      case t.Type.COMMENT:
      case t.Type.PLAIN:
        return new t.PlainValue(k, y);
      case t.Type.QUOTE_DOUBLE:
        return new v(k, y);
      case t.Type.QUOTE_SINGLE:
        return new D(k, y);
      default:
        return null;
    }
  }
  var x = class Ri {
    static parseType(y, b, h) {
      switch (y[b]) {
        case "*":
          return t.Type.ALIAS;
        case ">":
          return t.Type.BLOCK_FOLDED;
        case "|":
          return t.Type.BLOCK_LITERAL;
        case "{":
          return t.Type.FLOW_MAP;
        case "[":
          return t.Type.FLOW_SEQ;
        case "?":
          return !h && t.Node.atBlank(y, b + 1, !0) ? t.Type.MAP_KEY : t.Type.PLAIN;
        case ":":
          return !h && t.Node.atBlank(y, b + 1, !0) ? t.Type.MAP_VALUE : t.Type.PLAIN;
        case "-":
          return !h && t.Node.atBlank(y, b + 1, !0) ? t.Type.SEQ_ITEM : t.Type.PLAIN;
        case '"':
          return t.Type.QUOTE_DOUBLE;
        case "'":
          return t.Type.QUOTE_SINGLE;
        default:
          return t.Type.PLAIN;
      }
    }
    constructor(y = {}, { atLineStart: b, inCollection: h, inFlow: m, indent: p, lineStart: E, parent: w } = {}) {
      t._defineProperty(this, "parseNode", (L, C) => {
        if (t.Node.atDocumentBoundary(this.src, C)) return null;
        let A = new Ri(this, L), { props: _, type: O, valueStart: T } = A.parseProps(C), P = S(O, _), V = P.parse(A, T);
        if (P.range = new t.Range(C, V), V <= C && (P.error = new Error("Node#parse consumed no characters"), P.error.parseEnd = V, P.error.source = P, P.range.end = C + 1), A.nodeStartsCollection(P)) {
          !P.error && !A.atLineStart && A.parent.type === t.Type.DOCUMENT && (P.error = new t.YAMLSyntaxError(P, "Block collection must not have preceding content here (e.g. directives-end indicator)"));
          let Y = new a(P);
          return V = Y.parse(new Ri(A), V), Y.range = new t.Range(C, V), Y;
        }
        return P;
      }), this.atLineStart = b ?? (y.atLineStart || !1), this.inCollection = h ?? (y.inCollection || !1), this.inFlow = m ?? (y.inFlow || !1), this.indent = p ?? y.indent, this.lineStart = E ?? y.lineStart, this.parent = w ?? (y.parent || {}), this.root = y.root, this.src = y.src;
    }
    nodeStartsCollection(y) {
      let { inCollection: b, inFlow: h, src: m } = this;
      if (b || h) return !1;
      if (y instanceof r) return !0;
      let p = y.range.end;
      return m[p] === `
` || m[p - 1] === `
` ? !1 : (p = t.Node.endOfWhiteSpace(m, p), m[p] === ":");
    }
    parseProps(y) {
      let { inFlow: b, parent: h, src: m } = this, p = [], E = !1;
      y = this.atLineStart ? t.Node.endOfIndent(m, y) : t.Node.endOfWhiteSpace(m, y);
      let w = m[y];
      for (; w === t.Char.ANCHOR || w === t.Char.COMMENT || w === t.Char.TAG || w === `
`; ) {
        if (w === `
`) {
          let C = y, A;
          do
            A = C + 1, C = t.Node.endOfIndent(m, A);
          while (m[C] === `
`);
          let _ = C - (A + this.indent), O = h.type === t.Type.SEQ_ITEM && h.context.atLineStart;
          if (m[C] !== "#" && !t.Node.nextNodeIsIndented(m[C], _, !O)) break;
          this.atLineStart = !0, this.lineStart = A, E = !1, y = C;
        } else if (w === t.Char.COMMENT) {
          let C = t.Node.endOfLine(m, y + 1);
          p.push(new t.Range(y, C)), y = C;
        } else {
          let C = t.Node.endOfIdentifier(m, y + 1);
          w === t.Char.TAG && m[C] === "," && /^[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+,\d\d\d\d(-\d\d){0,2}\/\S/.test(m.slice(y + 1, C + 13)) && (C = t.Node.endOfIdentifier(m, C + 5)), p.push(new t.Range(y, C)), E = !0, y = t.Node.endOfWhiteSpace(m, C);
        }
        w = m[y];
      }
      E && w === ":" && t.Node.atBlank(m, y + 1, !0) && (y -= 1);
      let L = Ri.parseType(m, y, b);
      return { props: p, type: L, valueStart: y };
    }
  };
  function N(k) {
    let y = [];
    k.indexOf("\r") !== -1 && (k = k.replace(/\r\n?/g, (m, p) => (m.length > 1 && y.push(p), `
`)));
    let b = [], h = 0;
    do {
      let m = new l(), p = new x({ src: k });
      h = m.parse(p, h), b.push(m);
    } while (h < k.length);
    return b.setOrigRanges = () => {
      if (y.length === 0) return !1;
      for (let p = 1; p < y.length; ++p) y[p] -= p;
      let m = 0;
      for (let p = 0; p < b.length; ++p) m = b[p].setOrigRanges(y, m);
      return y.splice(0, y.length), !0;
    }, b.toString = () => b.join(`...
`), b;
  }
  e.parse = N;
}), ri = pn((e) => {
  var t = fr();
  function n(M, F, R) {
    return R ? `#${R.replace(/[\s\S]^/gm, `$&${F}#`)}
${F}${M}` : M;
  }
  function r(M, F, R) {
    return R ? R.indexOf(`
`) === -1 ? `${M} #${R}` : `${M}
` + R.replace(/^/gm, `${F || ""}#`) : M;
  }
  var s = class {
  };
  function i(M, F, R) {
    if (Array.isArray(M)) return M.map((I, B) => i(I, String(B), R));
    if (M && typeof M.toJSON == "function") {
      let I = R && R.anchors && R.anchors.get(M);
      I && (R.onCreate = (j) => {
        I.res = j, delete R.onCreate;
      });
      let B = M.toJSON(F, R);
      return I && R.onCreate && R.onCreate(B), B;
    }
    return (!R || !R.keep) && typeof M == "bigint" ? Number(M) : M;
  }
  var a = class extends s {
    constructor(M) {
      super(), this.value = M;
    }
    toJSON(M, F) {
      return F && F.keep ? this.value : i(this.value, M, F);
    }
    toString() {
      return String(this.value);
    }
  };
  function o(M, F, R) {
    let I = R;
    for (let B = F.length - 1; B >= 0; --B) {
      let j = F[B];
      if (Number.isInteger(j) && j >= 0) {
        let W = [];
        W[j] = I, I = W;
      } else {
        let W = {};
        Object.defineProperty(W, j, { value: I, writable: !0, enumerable: !0, configurable: !0 }), I = W;
      }
    }
    return M.createNode(I, !1);
  }
  var l = (M) => M == null || typeof M == "object" && M[Symbol.iterator]().next().done, u = class qn extends s {
    constructor(F) {
      super(), t._defineProperty(this, "items", []), this.schema = F;
    }
    addIn(F, R) {
      if (l(F)) this.add(R);
      else {
        let [I, ...B] = F, j = this.get(I, !0);
        if (j instanceof qn) j.addIn(B, R);
        else if (j === void 0 && this.schema) this.set(I, o(this.schema, B, R));
        else throw new Error(`Expected YAML collection at ${I}. Remaining path: ${B}`);
      }
    }
    deleteIn([F, ...R]) {
      if (R.length === 0) return this.delete(F);
      let I = this.get(F, !0);
      if (I instanceof qn) return I.deleteIn(R);
      throw new Error(`Expected YAML collection at ${F}. Remaining path: ${R}`);
    }
    getIn([F, ...R], I) {
      let B = this.get(F, !0);
      return R.length === 0 ? !I && B instanceof a ? B.value : B : B instanceof qn ? B.getIn(R, I) : void 0;
    }
    hasAllNullValues() {
      return this.items.every((F) => {
        if (!F || F.type !== "PAIR") return !1;
        let R = F.value;
        return R == null || R instanceof a && R.value == null && !R.commentBefore && !R.comment && !R.tag;
      });
    }
    hasIn([F, ...R]) {
      if (R.length === 0) return this.has(F);
      let I = this.get(F, !0);
      return I instanceof qn ? I.hasIn(R) : !1;
    }
    setIn([F, ...R], I) {
      if (R.length === 0) this.set(F, I);
      else {
        let B = this.get(F, !0);
        if (B instanceof qn) B.setIn(R, I);
        else if (B === void 0 && this.schema) this.set(F, o(this.schema, R, I));
        else throw new Error(`Expected YAML collection at ${F}. Remaining path: ${R}`);
      }
    }
    toJSON() {
      return null;
    }
    toString(F, { blockItem: R, flowChars: I, isMap: B, itemIndent: j }, W, H) {
      let { indent: G, indentStep: Q, stringify: ee } = F, se = this.type === t.Type.FLOW_MAP || this.type === t.Type.FLOW_SEQ || F.inFlow;
      se && (j += Q);
      let ke = B && this.hasAllNullValues();
      F = Object.assign({}, F, { allNullValues: ke, indent: j, inFlow: se, type: null });
      let de = !1, Ce = !1, ge = this.items.reduce((Ue, be, Te) => {
        let we;
        be && (!de && be.spaceBefore && Ue.push({ type: "comment", str: "" }), be.commentBefore && be.commentBefore.match(/^.*$/gm).forEach((Lg) => {
          Ue.push({ type: "comment", str: `#${Lg}` });
        }), be.comment && (we = be.comment), se && (!de && be.spaceBefore || be.commentBefore || be.comment || be.key && (be.key.commentBefore || be.key.comment) || be.value && (be.value.commentBefore || be.value.comment)) && (Ce = !0)), de = !1;
        let rt = ee(be, F, () => we = null, () => de = !0);
        return se && !Ce && rt.includes(`
`) && (Ce = !0), se && Te < this.items.length - 1 && (rt += ","), rt = r(rt, j, we), de && (we || se) && (de = !1), Ue.push({ type: "item", str: rt }), Ue;
      }, []), xe;
      if (ge.length === 0) xe = I.start + I.end;
      else if (se) {
        let { start: Ue, end: be } = I, Te = ge.map((we) => we.str);
        if (Ce || Te.reduce((we, rt) => we + rt.length + 2, 2) > qn.maxFlowStringSingleLineLength) {
          xe = Ue;
          for (let we of Te) xe += we ? `
${Q}${G}${we}` : `
`;
          xe += `
${G}${be}`;
        } else xe = `${Ue} ${Te.join(" ")} ${be}`;
      } else {
        let Ue = ge.map(R);
        xe = Ue.shift();
        for (let be of Ue) xe += be ? `
${G}${be}` : `
`;
      }
      return this.comment ? (xe += `
` + this.comment.replace(/^/gm, `${G}#`), W && W()) : de && H && H(), xe;
    }
  };
  t._defineProperty(u, "maxFlowStringSingleLineLength", 60);
  function f(M) {
    let F = M instanceof a ? M.value : M;
    return F && typeof F == "string" && (F = Number(F)), Number.isInteger(F) && F >= 0 ? F : null;
  }
  var c = class extends u {
    add(M) {
      this.items.push(M);
    }
    delete(M) {
      let F = f(M);
      return typeof F != "number" ? !1 : this.items.splice(F, 1).length > 0;
    }
    get(M, F) {
      let R = f(M);
      if (typeof R != "number") return;
      let I = this.items[R];
      return !F && I instanceof a ? I.value : I;
    }
    has(M) {
      let F = f(M);
      return typeof F == "number" && F < this.items.length;
    }
    set(M, F) {
      let R = f(M);
      if (typeof R != "number") throw new Error(`Expected a valid index, not ${M}.`);
      this.items[R] = F;
    }
    toJSON(M, F) {
      let R = [];
      F && F.onCreate && F.onCreate(R);
      let I = 0;
      for (let B of this.items) R.push(i(B, String(I++), F));
      return R;
    }
    toString(M, F, R) {
      return M ? super.toString(M, { blockItem: (I) => I.type === "comment" ? I.str : `- ${I.str}`, flowChars: { start: "[", end: "]" }, isMap: !1, itemIndent: (M.indent || "") + "  " }, F, R) : JSON.stringify(this);
    }
  }, d = (M, F, R) => F === null ? "" : typeof F != "object" ? String(F) : M instanceof s && R && R.doc ? M.toString({ anchors: /* @__PURE__ */ Object.create(null), doc: R.doc, indent: "", indentStep: R.indentStep, inFlow: !0, inStringifyKey: !0, stringify: R.stringify }) : JSON.stringify(F), v = class vm extends s {
    constructor(F, R = null) {
      super(), this.key = F, this.value = R, this.type = vm.Type.PAIR;
    }
    get commentBefore() {
      return this.key instanceof s ? this.key.commentBefore : void 0;
    }
    set commentBefore(F) {
      if (this.key == null && (this.key = new a(null)), this.key instanceof s) this.key.commentBefore = F;
      else {
        let R = "Pair.commentBefore is an alias for Pair.key.commentBefore. To set it, the key must be a Node.";
        throw new Error(R);
      }
    }
    addToJSMap(F, R) {
      let I = i(this.key, "", F);
      if (R instanceof Map) {
        let B = i(this.value, I, F);
        R.set(I, B);
      } else if (R instanceof Set) R.add(I);
      else {
        let B = d(this.key, I, F), j = i(this.value, B, F);
        B in R ? Object.defineProperty(R, B, { value: j, writable: !0, enumerable: !0, configurable: !0 }) : R[B] = j;
      }
      return R;
    }
    toJSON(F, R) {
      let I = R && R.mapAsMap ? /* @__PURE__ */ new Map() : {};
      return this.addToJSMap(R, I);
    }
    toString(F, R, I) {
      if (!F || !F.doc) return JSON.stringify(this);
      let { indent: B, indentSeq: j, simpleKeys: W } = F.doc.options, { key: H, value: G } = this, Q = H instanceof s && H.comment;
      if (W) {
        if (Q) throw new Error("With simple keys, key nodes cannot have comments");
        if (H instanceof u) {
          let rt = "With simple keys, collection cannot be used as a key value";
          throw new Error(rt);
        }
      }
      let ee = !W && (!H || Q || (H instanceof s ? H instanceof u || H.type === t.Type.BLOCK_FOLDED || H.type === t.Type.BLOCK_LITERAL : typeof H == "object")), { doc: se, indent: ke, indentStep: de, stringify: Ce } = F;
      F = Object.assign({}, F, { implicitKey: !ee, indent: ke + de });
      let ge = !1, xe = Ce(H, F, () => Q = null, () => ge = !0);
      if (xe = r(xe, F.indent, Q), !ee && xe.length > 1024) {
        if (W) throw new Error("With simple keys, single line scalar must not span more than 1024 characters");
        ee = !0;
      }
      if (F.allNullValues && !W) return this.comment ? (xe = r(xe, F.indent, this.comment), R && R()) : ge && !Q && I && I(), F.inFlow && !ee ? xe : `? ${xe}`;
      xe = ee ? `? ${xe}
${ke}:` : `${xe}:`, this.comment && (xe = r(xe, F.indent, this.comment), R && R());
      let Ue = "", be = null;
      if (G instanceof s) {
        if (G.spaceBefore && (Ue = `
`), G.commentBefore) {
          let rt = G.commentBefore.replace(/^/gm, `${F.indent}#`);
          Ue += `
${rt}`;
        }
        be = G.comment;
      } else G && typeof G == "object" && (G = se.schema.createNode(G, !0));
      F.implicitKey = !1, !ee && !this.comment && G instanceof a && (F.indentAtStart = xe.length + 1), ge = !1, !j && B >= 2 && !F.inFlow && !ee && G instanceof c && G.type !== t.Type.FLOW_SEQ && !G.tag && !se.anchors.getName(G) && (F.indent = F.indent.substr(2));
      let Te = Ce(G, F, () => be = null, () => ge = !0), we = " ";
      return Ue || this.comment ? we = `${Ue}
${F.indent}` : !ee && G instanceof u ? (!(Te[0] === "[" || Te[0] === "{") || Te.includes(`
`)) && (we = `
${F.indent}`) : Te[0] === `
` && (we = ""), ge && !be && I && I(), r(xe + we + Te, F.indent, be);
    }
  };
  t._defineProperty(v, "Type", { PAIR: "PAIR", MERGE_PAIR: "MERGE_PAIR" });
  var D = (M, F) => {
    if (M instanceof S) {
      let R = F.get(M.source);
      return R.count * R.aliasCount;
    } else if (M instanceof u) {
      let R = 0;
      for (let I of M.items) {
        let B = D(I, F);
        B > R && (R = B);
      }
      return R;
    } else if (M instanceof v) {
      let R = D(M.key, F), I = D(M.value, F);
      return Math.max(R, I);
    }
    return 1;
  }, S = class wm extends s {
    static stringify({ range: F, source: R }, { anchors: I, doc: B, implicitKey: j, inStringifyKey: W }) {
      let H = Object.keys(I).find((Q) => I[Q] === R);
      if (!H && W && (H = B.anchors.getName(R) || B.anchors.newName()), H) return `*${H}${j ? " " : ""}`;
      let G = B.anchors.getName(R) ? "Alias node must be after source node" : "Source node not found for alias node";
      throw new Error(`${G} [${F}]`);
    }
    constructor(F) {
      super(), this.source = F, this.type = t.Type.ALIAS;
    }
    set tag(F) {
      throw new Error("Alias nodes cannot have tags");
    }
    toJSON(F, R) {
      if (!R) return i(this.source, F, R);
      let { anchors: I, maxAliasCount: B } = R, j = I.get(this.source);
      if (!j || j.res === void 0) {
        let W = "This should not happen: Alias anchor was not resolved?";
        throw this.cstNode ? new t.YAMLReferenceError(this.cstNode, W) : new ReferenceError(W);
      }
      if (B >= 0 && (j.count += 1, j.aliasCount === 0 && (j.aliasCount = D(this.source, I)), j.count * j.aliasCount > B)) {
        let W = "Excessive alias count indicates a resource exhaustion attack";
        throw this.cstNode ? new t.YAMLReferenceError(this.cstNode, W) : new ReferenceError(W);
      }
      return j.res;
    }
    toString(F) {
      return wm.stringify(this, F);
    }
  };
  t._defineProperty(S, "default", !0);
  function x(M, F) {
    let R = F instanceof a ? F.value : F;
    for (let I of M) if (I instanceof v && (I.key === F || I.key === R || I.key && I.key.value === R)) return I;
  }
  var N = class extends u {
    add(M, F) {
      M ? M instanceof v || (M = new v(M.key || M, M.value)) : M = new v(M);
      let R = x(this.items, M.key), I = this.schema && this.schema.sortMapEntries;
      if (R) if (F) R.value = M.value;
      else throw new Error(`Key ${M.key} already set`);
      else if (I) {
        let B = this.items.findIndex((j) => I(M, j) < 0);
        B === -1 ? this.items.push(M) : this.items.splice(B, 0, M);
      } else this.items.push(M);
    }
    delete(M) {
      let F = x(this.items, M);
      return F ? this.items.splice(this.items.indexOf(F), 1).length > 0 : !1;
    }
    get(M, F) {
      let R = x(this.items, M), I = R && R.value;
      return !F && I instanceof a ? I.value : I;
    }
    has(M) {
      return !!x(this.items, M);
    }
    set(M, F) {
      this.add(new v(M, F), !0);
    }
    toJSON(M, F, R) {
      let I = R ? new R() : F && F.mapAsMap ? /* @__PURE__ */ new Map() : {};
      F && F.onCreate && F.onCreate(I);
      for (let B of this.items) B.addToJSMap(F, I);
      return I;
    }
    toString(M, F, R) {
      if (!M) return JSON.stringify(this);
      for (let I of this.items) if (!(I instanceof v)) throw new Error(`Map items must all be pairs; found ${JSON.stringify(I)} instead`);
      return super.toString(M, { blockItem: (I) => I.str, flowChars: { start: "{", end: "}" }, isMap: !0, itemIndent: M.indent || "" }, F, R);
    }
  }, k = "<<", y = class extends v {
    constructor(M) {
      if (M instanceof v) {
        let F = M.value;
        F instanceof c || (F = new c(), F.items.push(M.value), F.range = M.value.range), super(M.key, F), this.range = M.range;
      } else super(new a(k), new c());
      this.type = v.Type.MERGE_PAIR;
    }
    addToJSMap(M, F) {
      for (let { source: R } of this.value.items) {
        if (!(R instanceof N)) throw new Error("Merge sources must be maps");
        let I = R.toJSON(null, M, Map);
        for (let [B, j] of I) F instanceof Map ? F.has(B) || F.set(B, j) : F instanceof Set ? F.add(B) : Object.prototype.hasOwnProperty.call(F, B) || Object.defineProperty(F, B, { value: j, writable: !0, enumerable: !0, configurable: !0 });
      }
      return F;
    }
    toString(M, F) {
      let R = this.value;
      if (R.items.length > 1) return super.toString(M, F);
      this.value = R.items[0];
      let I = super.toString(M, F);
      return this.value = R, I;
    }
  }, b = { defaultType: t.Type.BLOCK_LITERAL, lineWidth: 76 }, h = { trueStr: "true", falseStr: "false" }, m = { asBigInt: !1 }, p = { nullStr: "null" }, E = { defaultType: t.Type.PLAIN, doubleQuoted: { jsonEncoding: !1, minMultiLineLength: 40 }, fold: { lineWidth: 80, minContentWidth: 20 } };
  function w(M, F, R) {
    for (let { format: I, test: B, resolve: j } of F) if (B) {
      let W = M.match(B);
      if (W) {
        let H = j.apply(null, W);
        return H instanceof a || (H = new a(H)), I && (H.format = I), H;
      }
    }
    return R && (M = R(M)), new a(M);
  }
  var L = "flow", C = "block", A = "quoted", _ = (M, F) => {
    let R = M[F + 1];
    for (; R === " " || R === "	"; ) {
      do
        R = M[F += 1];
      while (R && R !== `
`);
      R = M[F + 1];
    }
    return F;
  };
  function O(M, F, R, { indentAtStart: I, lineWidth: B = 80, minContentWidth: j = 20, onFold: W, onOverflow: H }) {
    if (!B || B < 0) return M;
    let G = Math.max(1 + j, 1 + B - F.length);
    if (M.length <= G) return M;
    let Q = [], ee = {}, se = B - F.length;
    typeof I == "number" && (I > B - Math.max(2, j) ? Q.push(0) : se = B - I);
    let ke, de, Ce = !1, ge = -1, xe = -1, Ue = -1;
    R === C && (ge = _(M, ge), ge !== -1 && (se = ge + G));
    for (let Te; Te = M[ge += 1]; ) {
      if (R === A && Te === "\\") {
        switch (xe = ge, M[ge + 1]) {
          case "x":
            ge += 3;
            break;
          case "u":
            ge += 5;
            break;
          case "U":
            ge += 9;
            break;
          default:
            ge += 1;
        }
        Ue = ge;
      }
      if (Te === `
`) R === C && (ge = _(M, ge)), se = ge + G, ke = void 0;
      else {
        if (Te === " " && de && de !== " " && de !== `
` && de !== "	") {
          let we = M[ge + 1];
          we && we !== " " && we !== `
` && we !== "	" && (ke = ge);
        }
        if (ge >= se) if (ke) Q.push(ke), se = ke + G, ke = void 0;
        else if (R === A) {
          for (; de === " " || de === "	"; ) de = Te, Te = M[ge += 1], Ce = !0;
          let we = ge > Ue + 1 ? ge - 2 : xe - 1;
          if (ee[we]) return M;
          Q.push(we), ee[we] = !0, se = we + G, ke = void 0;
        } else Ce = !0;
      }
      de = Te;
    }
    if (Ce && H && H(), Q.length === 0) return M;
    W && W();
    let be = M.slice(0, Q[0]);
    for (let Te = 0; Te < Q.length; ++Te) {
      let we = Q[Te], rt = Q[Te + 1] || M.length;
      we === 0 ? be = `
${F}${M.slice(0, rt)}` : (R === A && ee[we] && (be += `${M[we]}\\`), be += `
${F}${M.slice(we + 1, rt)}`);
    }
    return be;
  }
  var T = ({ indentAtStart: M }) => M ? Object.assign({ indentAtStart: M }, E.fold) : E.fold, P = (M) => /^(%|---|\.\.\.)/m.test(M);
  function V(M, F, R) {
    if (!F || F < 0) return !1;
    let I = F - R, B = M.length;
    if (B <= I) return !1;
    for (let j = 0, W = 0; j < B; ++j) if (M[j] === `
`) {
      if (j - W > I) return !0;
      if (W = j + 1, B - W <= I) return !1;
    }
    return !0;
  }
  function Y(M, F) {
    let { implicitKey: R } = F, { jsonEncoding: I, minMultiLineLength: B } = E.doubleQuoted, j = JSON.stringify(M);
    if (I) return j;
    let W = F.indent || (P(M) ? "  " : ""), H = "", G = 0;
    for (let Q = 0, ee = j[Q]; ee; ee = j[++Q]) if (ee === " " && j[Q + 1] === "\\" && j[Q + 2] === "n" && (H += j.slice(G, Q) + "\\ ", Q += 1, G = Q, ee = "\\"), ee === "\\") switch (j[Q + 1]) {
      case "u":
        {
          H += j.slice(G, Q);
          let se = j.substr(Q + 2, 4);
          switch (se) {
            case "0000":
              H += "\\0";
              break;
            case "0007":
              H += "\\a";
              break;
            case "000b":
              H += "\\v";
              break;
            case "001b":
              H += "\\e";
              break;
            case "0085":
              H += "\\N";
              break;
            case "00a0":
              H += "\\_";
              break;
            case "2028":
              H += "\\L";
              break;
            case "2029":
              H += "\\P";
              break;
            default:
              se.substr(0, 2) === "00" ? H += "\\x" + se.substr(2) : H += j.substr(Q, 6);
          }
          Q += 5, G = Q + 1;
        }
        break;
      case "n":
        if (R || j[Q + 2] === '"' || j.length < B) Q += 1;
        else {
          for (H += j.slice(G, Q) + `

`; j[Q + 2] === "\\" && j[Q + 3] === "n" && j[Q + 4] !== '"'; ) H += `
`, Q += 2;
          H += W, j[Q + 2] === " " && (H += "\\"), Q += 1, G = Q + 1;
        }
        break;
      default:
        Q += 1;
    }
    return H = G ? H + j.slice(G) : j, R ? H : O(H, W, A, T(F));
  }
  function K(M, F) {
    if (F.implicitKey) {
      if (/\n/.test(M)) return Y(M, F);
    } else if (/[ \t]\n|\n[ \t]/.test(M)) return Y(M, F);
    let R = F.indent || (P(M) ? "  " : ""), I = "'" + M.replace(/'/g, "''").replace(/\n+/g, `$&
${R}`) + "'";
    return F.implicitKey ? I : O(I, R, L, T(F));
  }
  function J({ comment: M, type: F, value: R }, I, B, j) {
    if (/\n[\t ]+$/.test(R) || /^\s*$/.test(R)) return Y(R, I);
    let W = I.indent || (I.forceBlockIndent || P(R) ? "  " : ""), H = W ? "2" : "1", G = F === t.Type.BLOCK_FOLDED ? !1 : F === t.Type.BLOCK_LITERAL ? !0 : !V(R, E.fold.lineWidth, W.length), Q = G ? "|" : ">";
    if (!R) return Q + `
`;
    let ee = "", se = "";
    if (R = R.replace(/[\n\t ]*$/, (de) => {
      let Ce = de.indexOf(`
`);
      return Ce === -1 ? Q += "-" : (R === de || Ce !== de.length - 1) && (Q += "+", j && j()), se = de.replace(/\n$/, ""), "";
    }).replace(/^[\n ]*/, (de) => {
      de.indexOf(" ") !== -1 && (Q += H);
      let Ce = de.match(/ +$/);
      return Ce ? (ee = de.slice(0, -Ce[0].length), Ce[0]) : (ee = de, "");
    }), se && (se = se.replace(/\n+(?!\n|$)/g, `$&${W}`)), ee && (ee = ee.replace(/\n+/g, `$&${W}`)), M && (Q += " #" + M.replace(/ ?[\r\n]+/g, " "), B && B()), !R) return `${Q}${H}
${W}${se}`;
    if (G) return R = R.replace(/\n+/g, `$&${W}`), `${Q}
${W}${ee}${R}${se}`;
    R = R.replace(/\n+/g, `
$&`).replace(/(?:^|\n)([\t ].*)(?:([\n\t ]*)\n(?![\n\t ]))?/g, "$1$2").replace(/\n+/g, `$&${W}`);
    let ke = O(`${ee}${R}${se}`, W, C, E.fold);
    return `${Q}
${W}${ke}`;
  }
  function $(M, F, R, I) {
    let { comment: B, type: j, value: W } = M, { actualString: H, implicitKey: G, indent: Q, inFlow: ee } = F;
    if (G && /[\n[\]{},]/.test(W) || ee && /[[\]{},]/.test(W)) return Y(W, F);
    if (!W || /^[\n\t ,[\]{}#&*!|>'"%@`]|^[?-]$|^[?-][ \t]|[\n:][ \t]|[ \t]\n|[\n\t ]#|[\n\t :]$/.test(W)) return G || ee || W.indexOf(`
`) === -1 ? W.indexOf('"') !== -1 && W.indexOf("'") === -1 ? K(W, F) : Y(W, F) : J(M, F, R, I);
    if (!G && !ee && j !== t.Type.PLAIN && W.indexOf(`
`) !== -1) return J(M, F, R, I);
    if (Q === "" && P(W)) return F.forceBlockIndent = !0, J(M, F, R, I);
    let se = W.replace(/\n+/g, `$&
${Q}`);
    if (H) {
      let { tags: de } = F.doc.schema;
      if (typeof w(se, de, de.scalarFallback).value != "string") return Y(W, F);
    }
    let ke = G ? se : O(se, Q, L, T(F));
    return B && !ee && (ke.indexOf(`
`) !== -1 || B.indexOf(`
`) !== -1) ? (R && R(), n(ke, Q, B)) : ke;
  }
  function z(M, F, R, I) {
    let { defaultType: B } = E, { implicitKey: j, inFlow: W } = F, { type: H, value: G } = M;
    typeof G != "string" && (G = String(G), M = Object.assign({}, M, { value: G }));
    let Q = (se) => {
      switch (se) {
        case t.Type.BLOCK_FOLDED:
        case t.Type.BLOCK_LITERAL:
          return J(M, F, R, I);
        case t.Type.QUOTE_DOUBLE:
          return Y(G, F);
        case t.Type.QUOTE_SINGLE:
          return K(G, F);
        case t.Type.PLAIN:
          return $(M, F, R, I);
        default:
          return null;
      }
    };
    (H !== t.Type.QUOTE_DOUBLE && /[\x00-\x08\x0b-\x1f\x7f-\x9f]/.test(G) || (j || W) && (H === t.Type.BLOCK_FOLDED || H === t.Type.BLOCK_LITERAL)) && (H = t.Type.QUOTE_DOUBLE);
    let ee = Q(H);
    if (ee === null && (ee = Q(B), ee === null)) throw new Error(`Unsupported default string type ${B}`);
    return ee;
  }
  function Z({ format: M, minFractionDigits: F, tag: R, value: I }) {
    if (typeof I == "bigint") return String(I);
    if (!isFinite(I)) return isNaN(I) ? ".nan" : I < 0 ? "-.inf" : ".inf";
    let B = JSON.stringify(I);
    if (!M && F && (!R || R === "tag:yaml.org,2002:float") && /^\d/.test(B)) {
      let j = B.indexOf(".");
      j < 0 && (j = B.length, B += ".");
      let W = F - (B.length - j - 1);
      for (; W-- > 0; ) B += "0";
    }
    return B;
  }
  function X(M, F) {
    let R, I;
    switch (F.type) {
      case t.Type.FLOW_MAP:
        R = "}", I = "flow map";
        break;
      case t.Type.FLOW_SEQ:
        R = "]", I = "flow sequence";
        break;
      default:
        M.push(new t.YAMLSemanticError(F, "Not a flow collection!?"));
        return;
    }
    let B;
    for (let j = F.items.length - 1; j >= 0; --j) {
      let W = F.items[j];
      if (!W || W.type !== t.Type.COMMENT) {
        B = W;
        break;
      }
    }
    if (B && B.char !== R) {
      let j = `Expected ${I} to end with ${R}`, W;
      typeof B.offset == "number" ? (W = new t.YAMLSemanticError(F, j), W.offset = B.offset + 1) : (W = new t.YAMLSemanticError(B, j), B.range && B.range.end && (W.offset = B.range.end - B.range.start)), M.push(W);
    }
  }
  function ne(M, F) {
    let R = F.context.src[F.range.start - 1];
    if (R !== `
` && R !== "	" && R !== " ") {
      let I = "Comments must be separated from other tokens by white space characters";
      M.push(new t.YAMLSemanticError(F, I));
    }
  }
  function le(M, F) {
    let R = String(F), I = R.substr(0, 8) + "..." + R.substr(-8);
    return new t.YAMLSemanticError(M, `The "${I}" key is too long`);
  }
  function nt(M, F) {
    for (let { afterKey: R, before: I, comment: B } of F) {
      let j = M.items[I];
      j ? (R && j.value && (j = j.value), B === void 0 ? (R || !j.commentBefore) && (j.spaceBefore = !0) : j.commentBefore ? j.commentBefore += `
` + B : j.commentBefore = B) : B !== void 0 && (M.comment ? M.comment += `
` + B : M.comment = B);
    }
  }
  function Zt(M, F) {
    let R = F.strValue;
    return R ? typeof R == "string" ? R : (R.errors.forEach((I) => {
      I.source || (I.source = F), M.errors.push(I);
    }), R.str) : "";
  }
  function en(M, F) {
    let { handle: R, suffix: I } = F.tag, B = M.tagPrefixes.find((j) => j.handle === R);
    if (!B) {
      let j = M.getDefaults().tagPrefixes;
      if (j && (B = j.find((W) => W.handle === R)), !B) throw new t.YAMLSemanticError(F, `The ${R} tag handle is non-default and was not declared.`);
    }
    if (!I) throw new t.YAMLSemanticError(F, `The ${R} tag has no suffix.`);
    if (R === "!" && (M.version || M.options.version) === "1.0") {
      if (I[0] === "^") return M.warnings.push(new t.YAMLWarning(F, "YAML 1.0 ^ tag expansion is not supported")), I;
      if (/[:/]/.test(I)) {
        let j = I.match(/^([a-z0-9-]+)\/(.*)/i);
        return j ? `tag:${j[1]}.yaml.org,2002:${j[2]}` : `tag:${I}`;
      }
    }
    return B.prefix + decodeURIComponent(I);
  }
  function Vt(M, F) {
    let { tag: R, type: I } = F, B = !1;
    if (R) {
      let { handle: j, suffix: W, verbatim: H } = R;
      if (H) {
        if (H !== "!" && H !== "!!") return H;
        let G = `Verbatim tags aren't resolved, so ${H} is invalid.`;
        M.errors.push(new t.YAMLSemanticError(F, G));
      } else if (j === "!" && !W) B = !0;
      else try {
        return en(M, F);
      } catch (G) {
        M.errors.push(G);
      }
    }
    switch (I) {
      case t.Type.BLOCK_FOLDED:
      case t.Type.BLOCK_LITERAL:
      case t.Type.QUOTE_DOUBLE:
      case t.Type.QUOTE_SINGLE:
        return t.defaultTags.STR;
      case t.Type.FLOW_MAP:
      case t.Type.MAP:
        return t.defaultTags.MAP;
      case t.Type.FLOW_SEQ:
      case t.Type.SEQ:
        return t.defaultTags.SEQ;
      case t.Type.PLAIN:
        return B ? t.defaultTags.STR : null;
      default:
        return null;
    }
  }
  function gs(M, F, R) {
    let { tags: I } = M.schema, B = [];
    for (let W of I) if (W.tag === R) if (W.test) B.push(W);
    else {
      let H = W.resolve(M, F);
      return H instanceof u ? H : new a(H);
    }
    let j = Zt(M, F);
    return typeof j == "string" && B.length > 0 ? w(j, B, I.scalarFallback) : null;
  }
  function li({ type: M }) {
    switch (M) {
      case t.Type.FLOW_MAP:
      case t.Type.MAP:
        return t.defaultTags.MAP;
      case t.Type.FLOW_SEQ:
      case t.Type.SEQ:
        return t.defaultTags.SEQ;
      default:
        return t.defaultTags.STR;
    }
  }
  function pg(M, F, R) {
    try {
      let I = gs(M, F, R);
      if (I) return R && F.tag && (I.tag = R), I;
    } catch (I) {
      return I.source || (I.source = F), M.errors.push(I), null;
    }
    try {
      let I = li(F);
      if (!I) throw new Error(`The tag ${R} is unavailable`);
      let B = `The tag ${R} is unavailable, falling back to ${I}`;
      M.warnings.push(new t.YAMLWarning(F, B));
      let j = gs(M, F, I);
      return j.tag = R, j;
    } catch (I) {
      let B = new t.YAMLReferenceError(F, I.message);
      return B.stack = I.stack, M.errors.push(B), null;
    }
  }
  var gg = (M) => {
    if (!M) return !1;
    let { type: F } = M;
    return F === t.Type.MAP_KEY || F === t.Type.MAP_VALUE || F === t.Type.SEQ_ITEM;
  };
  function yg(M, F) {
    let R = { before: [], after: [] }, I = !1, B = !1, j = gg(F.context.parent) ? F.context.parent.props.concat(F.props) : F.props;
    for (let { start: W, end: H } of j) switch (F.context.src[W]) {
      case t.Char.COMMENT: {
        if (!F.commentHasRequiredWhitespace(W)) {
          let ee = "Comments must be separated from other tokens by white space characters";
          M.push(new t.YAMLSemanticError(F, ee));
        }
        let { header: G, valueRange: Q } = F;
        (Q && (W > Q.start || G && W > G.start) ? R.after : R.before).push(F.context.src.slice(W + 1, H));
        break;
      }
      case t.Char.ANCHOR:
        if (I) {
          let G = "A node can have at most one anchor";
          M.push(new t.YAMLSemanticError(F, G));
        }
        I = !0;
        break;
      case t.Char.TAG:
        if (B) {
          let G = "A node can have at most one tag";
          M.push(new t.YAMLSemanticError(F, G));
        }
        B = !0;
        break;
    }
    return { comments: R, hasAnchor: I, hasTag: B };
  }
  function bg(M, F) {
    let { anchors: R, errors: I, schema: B } = M;
    if (F.type === t.Type.ALIAS) {
      let W = F.rawValue, H = R.getNode(W);
      if (!H) {
        let Q = `Aliased anchor not found: ${W}`;
        return I.push(new t.YAMLReferenceError(F, Q)), null;
      }
      let G = new S(H);
      return R._cstAliases.push(G), G;
    }
    let j = Vt(M, F);
    if (j) return pg(M, F, j);
    if (F.type !== t.Type.PLAIN) {
      let W = `Failed to resolve ${F.type} node here`;
      return I.push(new t.YAMLSyntaxError(F, W)), null;
    }
    try {
      let W = Zt(M, F);
      return w(W, B.tags, B.tags.scalarFallback);
    } catch (W) {
      return W.source || (W.source = F), I.push(W), null;
    }
  }
  function Sn(M, F) {
    if (!F) return null;
    F.error && M.errors.push(F.error);
    let { comments: R, hasAnchor: I, hasTag: B } = yg(M.errors, F);
    if (I) {
      let { anchors: W } = M, H = F.anchor, G = W.getNode(H);
      G && (W.map[W.newName(H)] = G), W.map[H] = F;
    }
    if (F.type === t.Type.ALIAS && (I || B)) {
      let W = "An alias node must not specify any properties";
      M.errors.push(new t.YAMLSemanticError(F, W));
    }
    let j = bg(M, F);
    if (j) {
      j.range = [F.range.start, F.range.end], M.options.keepCstNodes && (j.cstNode = F), M.options.keepNodeTypes && (j.type = F.type);
      let W = R.before.join(`
`);
      W && (j.commentBefore = j.commentBefore ? `${j.commentBefore}
${W}` : W);
      let H = R.after.join(`
`);
      H && (j.comment = j.comment ? `${j.comment}
${H}` : H);
    }
    return F.resolved = j;
  }
  function vg(M, F) {
    if (F.type !== t.Type.MAP && F.type !== t.Type.FLOW_MAP) {
      let W = `A ${F.type} node cannot be resolved as a mapping`;
      return M.errors.push(new t.YAMLSyntaxError(F, W)), null;
    }
    let { comments: R, items: I } = F.type === t.Type.FLOW_MAP ? Eg(M, F) : Sg(M, F), B = new N();
    B.items = I, nt(B, R);
    let j = !1;
    for (let W = 0; W < I.length; ++W) {
      let { key: H } = I[W];
      if (H instanceof u && (j = !0), M.schema.merge && H && H.value === k) {
        I[W] = new y(I[W]);
        let G = I[W].value.items, Q = null;
        G.some((ee) => {
          if (ee instanceof S) {
            let { type: se } = ee.source;
            return se === t.Type.MAP || se === t.Type.FLOW_MAP ? !1 : Q = "Merge nodes aliases can only point to maps";
          }
          return Q = "Merge nodes can only have Alias nodes as values";
        }), Q && M.errors.push(new t.YAMLSemanticError(F, Q));
      } else for (let G = W + 1; G < I.length; ++G) {
        let { key: Q } = I[G];
        if (H === Q || H && Q && Object.prototype.hasOwnProperty.call(H, "value") && H.value === Q.value) {
          let ee = `Map keys must be unique; "${H}" is repeated`;
          M.errors.push(new t.YAMLSemanticError(F, ee));
          break;
        }
      }
    }
    if (j && !M.options.mapAsMap) {
      let W = "Keys with collection values will be stringified as YAML due to JS Object restrictions. Use mapAsMap: true to avoid this.";
      M.warnings.push(new t.YAMLWarning(F, W));
    }
    return F.resolved = B, B;
  }
  var wg = ({ context: { lineStart: M, node: F, src: R }, props: I }) => {
    if (I.length === 0) return !1;
    let { start: B } = I[0];
    if (F && B > F.valueRange.start || R[B] !== t.Char.COMMENT) return !1;
    for (let j = M; j < B; ++j) if (R[j] === `
`) return !1;
    return !0;
  };
  function Dg(M, F) {
    if (!wg(M)) return;
    let R = M.getPropValue(0, t.Char.COMMENT, !0), I = !1, B = F.value.commentBefore;
    if (B && B.startsWith(R)) F.value.commentBefore = B.substr(R.length + 1), I = !0;
    else {
      let j = F.value.comment;
      !M.node && j && j.startsWith(R) && (F.value.comment = j.substr(R.length + 1), I = !0);
    }
    I && (F.comment = R);
  }
  function Sg(M, F) {
    let R = [], I = [], B, j = null;
    for (let W = 0; W < F.items.length; ++W) {
      let H = F.items[W];
      switch (H.type) {
        case t.Type.BLANK_LINE:
          R.push({ afterKey: !!B, before: I.length });
          break;
        case t.Type.COMMENT:
          R.push({ afterKey: !!B, before: I.length, comment: H.comment });
          break;
        case t.Type.MAP_KEY:
          B !== void 0 && I.push(new v(B)), H.error && M.errors.push(H.error), B = Sn(M, H.node), j = null;
          break;
        case t.Type.MAP_VALUE:
          {
            if (B === void 0 && (B = null), H.error && M.errors.push(H.error), !H.context.atLineStart && H.node && H.node.type === t.Type.MAP && !H.node.context.atLineStart) {
              let ee = "Nested mappings are not allowed in compact mappings";
              M.errors.push(new t.YAMLSemanticError(H.node, ee));
            }
            let G = H.node;
            if (!G && H.props.length > 0) {
              G = new t.PlainValue(t.Type.PLAIN, []), G.context = { parent: H, src: H.context.src };
              let ee = H.range.start + 1;
              if (G.range = { start: ee, end: ee }, G.valueRange = { start: ee, end: ee }, typeof H.range.origStart == "number") {
                let se = H.range.origStart + 1;
                G.range.origStart = G.range.origEnd = se, G.valueRange.origStart = G.valueRange.origEnd = se;
              }
            }
            let Q = new v(B, Sn(M, G));
            Dg(H, Q), I.push(Q), B && typeof j == "number" && H.range.start > j + 1024 && M.errors.push(le(F, B)), B = void 0, j = null;
          }
          break;
        default:
          B !== void 0 && I.push(new v(B)), B = Sn(M, H), j = H.range.start, H.error && M.errors.push(H.error);
          e: for (let G = W + 1; ; ++G) {
            let Q = F.items[G];
            switch (Q && Q.type) {
              case t.Type.BLANK_LINE:
              case t.Type.COMMENT:
                continue e;
              case t.Type.MAP_VALUE:
                break e;
              default: {
                let ee = "Implicit map keys need to be followed by map values";
                M.errors.push(new t.YAMLSemanticError(H, ee));
                break e;
              }
            }
          }
          if (H.valueRangeContainsNewline) {
            let G = "Implicit map keys need to be on a single line";
            M.errors.push(new t.YAMLSemanticError(H, G));
          }
      }
    }
    return B !== void 0 && I.push(new v(B)), { comments: R, items: I };
  }
  function Eg(M, F) {
    let R = [], I = [], B, j = !1, W = "{";
    for (let H = 0; H < F.items.length; ++H) {
      let G = F.items[H];
      if (typeof G.char == "string") {
        let { char: Q, offset: ee } = G;
        if (Q === "?" && B === void 0 && !j) {
          j = !0, W = ":";
          continue;
        }
        if (Q === ":") {
          if (B === void 0 && (B = null), W === ":") {
            W = ",";
            continue;
          }
        } else if (j && (B === void 0 && Q !== "," && (B = null), j = !1), B !== void 0 && (I.push(new v(B)), B = void 0, Q === ",")) {
          W = ":";
          continue;
        }
        if (Q === "}") {
          if (H === F.items.length - 1) continue;
        } else if (Q === W) {
          W = ":";
          continue;
        }
        let se = `Flow map contains an unexpected ${Q}`, ke = new t.YAMLSyntaxError(F, se);
        ke.offset = ee, M.errors.push(ke);
      } else G.type === t.Type.BLANK_LINE ? R.push({ afterKey: !!B, before: I.length }) : G.type === t.Type.COMMENT ? (ne(M.errors, G), R.push({ afterKey: !!B, before: I.length, comment: G.comment })) : B === void 0 ? (W === "," && M.errors.push(new t.YAMLSemanticError(G, "Separator , missing in flow map")), B = Sn(M, G)) : (W !== "," && M.errors.push(new t.YAMLSemanticError(G, "Indicator : missing in flow map entry")), I.push(new v(B, Sn(M, G))), B = void 0, j = !1);
    }
    return X(M.errors, F), B !== void 0 && I.push(new v(B)), { comments: R, items: I };
  }
  function Ag(M, F) {
    if (F.type !== t.Type.SEQ && F.type !== t.Type.FLOW_SEQ) {
      let j = `A ${F.type} node cannot be resolved as a sequence`;
      return M.errors.push(new t.YAMLSyntaxError(F, j)), null;
    }
    let { comments: R, items: I } = F.type === t.Type.FLOW_SEQ ? Ng(M, F) : xg(M, F), B = new c();
    if (B.items = I, nt(B, R), !M.options.mapAsMap && I.some((j) => j instanceof v && j.key instanceof u)) {
      let j = "Keys with collection values will be stringified as YAML due to JS Object restrictions. Use mapAsMap: true to avoid this.";
      M.warnings.push(new t.YAMLWarning(F, j));
    }
    return F.resolved = B, B;
  }
  function xg(M, F) {
    let R = [], I = [];
    for (let B = 0; B < F.items.length; ++B) {
      let j = F.items[B];
      switch (j.type) {
        case t.Type.BLANK_LINE:
          R.push({ before: I.length });
          break;
        case t.Type.COMMENT:
          R.push({ comment: j.comment, before: I.length });
          break;
        case t.Type.SEQ_ITEM:
          if (j.error && M.errors.push(j.error), I.push(Sn(M, j.node)), j.hasProps) {
            let W = "Sequence items cannot have tags or anchors before the - indicator";
            M.errors.push(new t.YAMLSemanticError(j, W));
          }
          break;
        default:
          j.error && M.errors.push(j.error), M.errors.push(new t.YAMLSyntaxError(j, `Unexpected ${j.type} node in sequence`));
      }
    }
    return { comments: R, items: I };
  }
  function Ng(M, F) {
    let R = [], I = [], B = !1, j, W = null, H = "[", G = null;
    for (let Q = 0; Q < F.items.length; ++Q) {
      let ee = F.items[Q];
      if (typeof ee.char == "string") {
        let { char: se, offset: ke } = ee;
        if (se !== ":" && (B || j !== void 0) && (B && j === void 0 && (j = H ? I.pop() : null), I.push(new v(j)), B = !1, j = void 0, W = null), se === H) H = null;
        else if (!H && se === "?") B = !0;
        else if (H !== "[" && se === ":" && j === void 0) {
          if (H === ",") {
            if (j = I.pop(), j instanceof v) {
              let de = "Chaining flow sequence pairs is invalid", Ce = new t.YAMLSemanticError(F, de);
              Ce.offset = ke, M.errors.push(Ce);
            }
            if (!B && typeof W == "number") {
              let de = ee.range ? ee.range.start : ee.offset;
              de > W + 1024 && M.errors.push(le(F, j));
              let { src: Ce } = G.context;
              for (let ge = W; ge < de; ++ge) if (Ce[ge] === `
`) {
                let xe = "Implicit keys of flow sequence pairs need to be on a single line";
                M.errors.push(new t.YAMLSemanticError(G, xe));
                break;
              }
            }
          } else j = null;
          W = null, B = !1, H = null;
        } else if (H === "[" || se !== "]" || Q < F.items.length - 1) {
          let de = `Flow sequence contains an unexpected ${se}`, Ce = new t.YAMLSyntaxError(F, de);
          Ce.offset = ke, M.errors.push(Ce);
        }
      } else if (ee.type === t.Type.BLANK_LINE) R.push({ before: I.length });
      else if (ee.type === t.Type.COMMENT) ne(M.errors, ee), R.push({ comment: ee.comment, before: I.length });
      else {
        if (H) {
          let ke = `Expected a ${H} in flow sequence`;
          M.errors.push(new t.YAMLSemanticError(ee, ke));
        }
        let se = Sn(M, ee);
        j === void 0 ? (I.push(se), G = ee) : (I.push(new v(j, se)), j = void 0), W = ee.range.start, H = ",";
      }
    }
    return X(M.errors, F), j !== void 0 && I.push(new v(j)), { comments: R, items: I };
  }
  e.Alias = S, e.Collection = u, e.Merge = y, e.Node = s, e.Pair = v, e.Scalar = a, e.YAMLMap = N, e.YAMLSeq = c, e.addComment = r, e.binaryOptions = b, e.boolOptions = h, e.findPair = x, e.intOptions = m, e.isEmptyPath = l, e.nullOptions = p, e.resolveMap = vg, e.resolveNode = Sn, e.resolveSeq = Ag, e.resolveString = Zt, e.strOptions = E, e.stringifyNumber = Z, e.stringifyString = z, e.toJSON = i;
}), Dm = pn((e) => {
  var t = fr(), n = ri(), r = { identify: (w) => w instanceof Uint8Array, default: !1, tag: "tag:yaml.org,2002:binary", resolve: (w, L) => {
    let C = n.resolveString(w, L);
    if (typeof Buffer == "function") return Buffer.from(C, "base64");
    if (typeof atob == "function") {
      let A = atob(C.replace(/[\n\r]/g, "")), _ = new Uint8Array(A.length);
      for (let O = 0; O < A.length; ++O) _[O] = A.charCodeAt(O);
      return _;
    } else {
      let A = "This environment does not support reading binary tags; either Buffer or atob is required";
      return w.errors.push(new t.YAMLReferenceError(L, A)), null;
    }
  }, options: n.binaryOptions, stringify: ({ comment: w, type: L, value: C }, A, _, O) => {
    let T;
    if (typeof Buffer == "function") T = C instanceof Buffer ? C.toString("base64") : Buffer.from(C.buffer).toString("base64");
    else if (typeof btoa == "function") {
      let P = "";
      for (let V = 0; V < C.length; ++V) P += String.fromCharCode(C[V]);
      T = btoa(P);
    } else throw new Error("This environment does not support writing binary tags; either Buffer or btoa is required");
    if (L || (L = n.binaryOptions.defaultType), L === t.Type.QUOTE_DOUBLE) C = T;
    else {
      let { lineWidth: P } = n.binaryOptions, V = Math.ceil(T.length / P), Y = new Array(V);
      for (let K = 0, J = 0; K < V; ++K, J += P) Y[K] = T.substr(J, P);
      C = Y.join(L === t.Type.BLOCK_LITERAL ? `
` : " ");
    }
    return n.stringifyString({ comment: w, type: L, value: C }, A, _, O);
  } };
  function s(w, L) {
    let C = n.resolveSeq(w, L);
    for (let A = 0; A < C.items.length; ++A) {
      let _ = C.items[A];
      if (!(_ instanceof n.Pair)) {
        if (_ instanceof n.YAMLMap) {
          if (_.items.length > 1) {
            let T = "Each pair must have its own sequence indicator";
            throw new t.YAMLSemanticError(L, T);
          }
          let O = _.items[0] || new n.Pair();
          _.commentBefore && (O.commentBefore = O.commentBefore ? `${_.commentBefore}
${O.commentBefore}` : _.commentBefore), _.comment && (O.comment = O.comment ? `${_.comment}
${O.comment}` : _.comment), _ = O;
        }
        C.items[A] = _ instanceof n.Pair ? _ : new n.Pair(_);
      }
    }
    return C;
  }
  function i(w, L, C) {
    let A = new n.YAMLSeq(w);
    A.tag = "tag:yaml.org,2002:pairs";
    for (let _ of L) {
      let O, T;
      if (Array.isArray(_)) if (_.length === 2) O = _[0], T = _[1];
      else throw new TypeError(`Expected [key, value] tuple: ${_}`);
      else if (_ && _ instanceof Object) {
        let V = Object.keys(_);
        if (V.length === 1) O = V[0], T = _[O];
        else throw new TypeError(`Expected { key: value } tuple: ${_}`);
      } else O = _;
      let P = w.createPair(O, T, C);
      A.items.push(P);
    }
    return A;
  }
  var a = { default: !1, tag: "tag:yaml.org,2002:pairs", resolve: s, createNode: i }, o = class Sm extends n.YAMLSeq {
    constructor() {
      super(), t._defineProperty(this, "add", n.YAMLMap.prototype.add.bind(this)), t._defineProperty(this, "delete", n.YAMLMap.prototype.delete.bind(this)), t._defineProperty(this, "get", n.YAMLMap.prototype.get.bind(this)), t._defineProperty(this, "has", n.YAMLMap.prototype.has.bind(this)), t._defineProperty(this, "set", n.YAMLMap.prototype.set.bind(this)), this.tag = Sm.tag;
    }
    toJSON(L, C) {
      let A = /* @__PURE__ */ new Map();
      C && C.onCreate && C.onCreate(A);
      for (let _ of this.items) {
        let O, T;
        if (_ instanceof n.Pair ? (O = n.toJSON(_.key, "", C), T = n.toJSON(_.value, O, C)) : O = n.toJSON(_, "", C), A.has(O)) throw new Error("Ordered maps must not include duplicate keys");
        A.set(O, T);
      }
      return A;
    }
  };
  t._defineProperty(o, "tag", "tag:yaml.org,2002:omap");
  function l(w, L) {
    let C = s(w, L), A = [];
    for (let { key: _ } of C.items) if (_ instanceof n.Scalar) if (A.includes(_.value)) {
      let O = "Ordered maps must not include duplicate keys";
      throw new t.YAMLSemanticError(L, O);
    } else A.push(_.value);
    return Object.assign(new o(), C);
  }
  function u(w, L, C) {
    let A = i(w, L, C), _ = new o();
    return _.items = A.items, _;
  }
  var f = { identify: (w) => w instanceof Map, nodeClass: o, default: !1, tag: "tag:yaml.org,2002:omap", resolve: l, createNode: u }, c = class Em extends n.YAMLMap {
    constructor() {
      super(), this.tag = Em.tag;
    }
    add(L) {
      let C = L instanceof n.Pair ? L : new n.Pair(L);
      n.findPair(this.items, C.key) || this.items.push(C);
    }
    get(L, C) {
      let A = n.findPair(this.items, L);
      return !C && A instanceof n.Pair ? A.key instanceof n.Scalar ? A.key.value : A.key : A;
    }
    set(L, C) {
      if (typeof C != "boolean") throw new Error(`Expected boolean value for set(key, value) in a YAML set, not ${typeof C}`);
      let A = n.findPair(this.items, L);
      A && !C ? this.items.splice(this.items.indexOf(A), 1) : !A && C && this.items.push(new n.Pair(L));
    }
    toJSON(L, C) {
      return super.toJSON(L, C, Set);
    }
    toString(L, C, A) {
      if (!L) return JSON.stringify(this);
      if (this.hasAllNullValues()) return super.toString(L, C, A);
      throw new Error("Set items must all have null values");
    }
  };
  t._defineProperty(c, "tag", "tag:yaml.org,2002:set");
  function d(w, L) {
    let C = n.resolveMap(w, L);
    if (!C.hasAllNullValues()) throw new t.YAMLSemanticError(L, "Set items must all have null values");
    return Object.assign(new c(), C);
  }
  function v(w, L, C) {
    let A = new c();
    for (let _ of L) A.items.push(w.createPair(_, null, C));
    return A;
  }
  var D = { identify: (w) => w instanceof Set, nodeClass: c, default: !1, tag: "tag:yaml.org,2002:set", resolve: d, createNode: v }, S = (w, L) => {
    let C = L.split(":").reduce((A, _) => A * 60 + Number(_), 0);
    return w === "-" ? -C : C;
  }, x = ({ value: w }) => {
    if (isNaN(w) || !isFinite(w)) return n.stringifyNumber(w);
    let L = "";
    w < 0 && (L = "-", w = Math.abs(w));
    let C = [w % 60];
    return w < 60 ? C.unshift(0) : (w = Math.round((w - C[0]) / 60), C.unshift(w % 60), w >= 60 && (w = Math.round((w - C[0]) / 60), C.unshift(w))), L + C.map((A) => A < 10 ? "0" + String(A) : String(A)).join(":").replace(/000000\d*$/, "");
  }, N = { identify: (w) => typeof w == "number", default: !0, tag: "tag:yaml.org,2002:int", format: "TIME", test: /^([-+]?)([0-9][0-9_]*(?::[0-5]?[0-9])+)$/, resolve: (w, L, C) => S(L, C.replace(/_/g, "")), stringify: x }, k = { identify: (w) => typeof w == "number", default: !0, tag: "tag:yaml.org,2002:float", format: "TIME", test: /^([-+]?)([0-9][0-9_]*(?::[0-5]?[0-9])+\.[0-9_]*)$/, resolve: (w, L, C) => S(L, C.replace(/_/g, "")), stringify: x }, y = { identify: (w) => w instanceof Date, default: !0, tag: "tag:yaml.org,2002:timestamp", test: RegExp("^(?:([0-9]{4})-([0-9]{1,2})-([0-9]{1,2})(?:(?:t|T|[ \\t]+)([0-9]{1,2}):([0-9]{1,2}):([0-9]{1,2}(\\.[0-9]+)?)(?:[ \\t]*(Z|[-+][012]?[0-9](?::[0-9]{2})?))?)?)$"), resolve: (w, L, C, A, _, O, T, P, V) => {
    P && (P = (P + "00").substr(1, 3));
    let Y = Date.UTC(L, C - 1, A, _ || 0, O || 0, T || 0, P || 0);
    if (V && V !== "Z") {
      let K = S(V[0], V.slice(1));
      Math.abs(K) < 30 && (K *= 60), Y -= 6e4 * K;
    }
    return new Date(Y);
  }, stringify: ({ value: w }) => w.toISOString().replace(/((T00:00)?:00)?\.000Z$/, "") };
  function b(w) {
    let L = {};
    return w ? typeof YAML_SILENCE_DEPRECATION_WARNINGS < "u" ? !YAML_SILENCE_DEPRECATION_WARNINGS : !L.YAML_SILENCE_DEPRECATION_WARNINGS : typeof YAML_SILENCE_WARNINGS < "u" ? !YAML_SILENCE_WARNINGS : !L.YAML_SILENCE_WARNINGS;
  }
  function h(w, L) {
    b(!1) && console.warn(L ? `${L}: ${w}` : w);
  }
  function m(w) {
    if (b(!0)) {
      let L = w.replace(/.*yaml[/\\]/i, "").replace(/\.js$/, "").replace(/\\/g, "/");
      h(`The endpoint 'yaml/${L}' will be removed in a future release.`, "DeprecationWarning");
    }
  }
  var p = {};
  function E(w, L) {
    if (!p[w] && b(!0)) {
      p[w] = !0;
      let C = `The option '${w}' will be removed in a future release`;
      C += L ? `, use '${L}' instead.` : ".", h(C, "DeprecationWarning");
    }
  }
  e.binary = r, e.floatTime = k, e.intTime = N, e.omap = f, e.pairs = a, e.set = D, e.timestamp = y, e.warn = h, e.warnFileDeprecation = m, e.warnOptionDeprecation = E;
}), Am = pn((e) => {
  var t = fr(), n = ri(), r = Dm();
  function s($, z, Z) {
    let X = new n.YAMLMap($);
    if (z instanceof Map) for (let [ne, le] of z) X.items.push($.createPair(ne, le, Z));
    else if (z && typeof z == "object") for (let ne of Object.keys(z)) X.items.push($.createPair(ne, z[ne], Z));
    return typeof $.sortMapEntries == "function" && X.items.sort($.sortMapEntries), X;
  }
  var i = { createNode: s, default: !0, nodeClass: n.YAMLMap, tag: "tag:yaml.org,2002:map", resolve: n.resolveMap };
  function a($, z, Z) {
    let X = new n.YAMLSeq($);
    if (z && z[Symbol.iterator]) for (let ne of z) {
      let le = $.createNode(ne, Z.wrapScalars, null, Z);
      X.items.push(le);
    }
    return X;
  }
  var o = { createNode: a, default: !0, nodeClass: n.YAMLSeq, tag: "tag:yaml.org,2002:seq", resolve: n.resolveSeq }, l = { identify: ($) => typeof $ == "string", default: !0, tag: "tag:yaml.org,2002:str", resolve: n.resolveString, stringify($, z, Z, X) {
    return z = Object.assign({ actualString: !0 }, z), n.stringifyString($, z, Z, X);
  }, options: n.strOptions }, u = [i, o, l], f = ($) => typeof $ == "bigint" || Number.isInteger($), c = ($, z, Z) => n.intOptions.asBigInt ? BigInt($) : parseInt(z, Z);
  function d($, z, Z) {
    let { value: X } = $;
    return f(X) && X >= 0 ? Z + X.toString(z) : n.stringifyNumber($);
  }
  var v = { identify: ($) => $ == null, createNode: ($, z, Z) => Z.wrapScalars ? new n.Scalar(null) : null, default: !0, tag: "tag:yaml.org,2002:null", test: /^(?:~|[Nn]ull|NULL)?$/, resolve: () => null, options: n.nullOptions, stringify: () => n.nullOptions.nullStr }, D = { identify: ($) => typeof $ == "boolean", default: !0, tag: "tag:yaml.org,2002:bool", test: /^(?:[Tt]rue|TRUE|[Ff]alse|FALSE)$/, resolve: ($) => $[0] === "t" || $[0] === "T", options: n.boolOptions, stringify: ({ value: $ }) => $ ? n.boolOptions.trueStr : n.boolOptions.falseStr }, S = { identify: ($) => f($) && $ >= 0, default: !0, tag: "tag:yaml.org,2002:int", format: "OCT", test: /^0o([0-7]+)$/, resolve: ($, z) => c($, z, 8), options: n.intOptions, stringify: ($) => d($, 8, "0o") }, x = { identify: f, default: !0, tag: "tag:yaml.org,2002:int", test: /^[-+]?[0-9]+$/, resolve: ($) => c($, $, 10), options: n.intOptions, stringify: n.stringifyNumber }, N = { identify: ($) => f($) && $ >= 0, default: !0, tag: "tag:yaml.org,2002:int", format: "HEX", test: /^0x([0-9a-fA-F]+)$/, resolve: ($, z) => c($, z, 16), options: n.intOptions, stringify: ($) => d($, 16, "0x") }, k = { identify: ($) => typeof $ == "number", default: !0, tag: "tag:yaml.org,2002:float", test: /^(?:[-+]?\.inf|(\.nan))$/i, resolve: ($, z) => z ? NaN : $[0] === "-" ? Number.NEGATIVE_INFINITY : Number.POSITIVE_INFINITY, stringify: n.stringifyNumber }, y = { identify: ($) => typeof $ == "number", default: !0, tag: "tag:yaml.org,2002:float", format: "EXP", test: /^[-+]?(?:\.[0-9]+|[0-9]+(?:\.[0-9]*)?)[eE][-+]?[0-9]+$/, resolve: ($) => parseFloat($), stringify: ({ value: $ }) => Number($).toExponential() }, b = { identify: ($) => typeof $ == "number", default: !0, tag: "tag:yaml.org,2002:float", test: /^[-+]?(?:\.([0-9]+)|[0-9]+\.([0-9]*))$/, resolve($, z, Z) {
    let X = z || Z, ne = new n.Scalar(parseFloat($));
    return X && X[X.length - 1] === "0" && (ne.minFractionDigits = X.length), ne;
  }, stringify: n.stringifyNumber }, h = u.concat([v, D, S, x, N, k, y, b]), m = ($) => typeof $ == "bigint" || Number.isInteger($), p = ({ value: $ }) => JSON.stringify($), E = [i, o, { identify: ($) => typeof $ == "string", default: !0, tag: "tag:yaml.org,2002:str", resolve: n.resolveString, stringify: p }, { identify: ($) => $ == null, createNode: ($, z, Z) => Z.wrapScalars ? new n.Scalar(null) : null, default: !0, tag: "tag:yaml.org,2002:null", test: /^null$/, resolve: () => null, stringify: p }, { identify: ($) => typeof $ == "boolean", default: !0, tag: "tag:yaml.org,2002:bool", test: /^true|false$/, resolve: ($) => $ === "true", stringify: p }, { identify: m, default: !0, tag: "tag:yaml.org,2002:int", test: /^-?(?:0|[1-9][0-9]*)$/, resolve: ($) => n.intOptions.asBigInt ? BigInt($) : parseInt($, 10), stringify: ({ value: $ }) => m($) ? $.toString() : JSON.stringify($) }, { identify: ($) => typeof $ == "number", default: !0, tag: "tag:yaml.org,2002:float", test: /^-?(?:0|[1-9][0-9]*)(?:\.[0-9]*)?(?:[eE][-+]?[0-9]+)?$/, resolve: ($) => parseFloat($), stringify: p }];
  E.scalarFallback = ($) => {
    throw new SyntaxError(`Unresolved plain scalar ${JSON.stringify($)}`);
  };
  var w = ({ value: $ }) => $ ? n.boolOptions.trueStr : n.boolOptions.falseStr, L = ($) => typeof $ == "bigint" || Number.isInteger($);
  function C($, z, Z) {
    let X = z.replace(/_/g, "");
    if (n.intOptions.asBigInt) {
      switch (Z) {
        case 2:
          X = `0b${X}`;
          break;
        case 8:
          X = `0o${X}`;
          break;
        case 16:
          X = `0x${X}`;
          break;
      }
      let le = BigInt(X);
      return $ === "-" ? BigInt(-1) * le : le;
    }
    let ne = parseInt(X, Z);
    return $ === "-" ? -1 * ne : ne;
  }
  function A($, z, Z) {
    let { value: X } = $;
    if (L(X)) {
      let ne = X.toString(z);
      return X < 0 ? "-" + Z + ne.substr(1) : Z + ne;
    }
    return n.stringifyNumber($);
  }
  var _ = u.concat([{ identify: ($) => $ == null, createNode: ($, z, Z) => Z.wrapScalars ? new n.Scalar(null) : null, default: !0, tag: "tag:yaml.org,2002:null", test: /^(?:~|[Nn]ull|NULL)?$/, resolve: () => null, options: n.nullOptions, stringify: () => n.nullOptions.nullStr }, { identify: ($) => typeof $ == "boolean", default: !0, tag: "tag:yaml.org,2002:bool", test: /^(?:Y|y|[Yy]es|YES|[Tt]rue|TRUE|[Oo]n|ON)$/, resolve: () => !0, options: n.boolOptions, stringify: w }, { identify: ($) => typeof $ == "boolean", default: !0, tag: "tag:yaml.org,2002:bool", test: /^(?:N|n|[Nn]o|NO|[Ff]alse|FALSE|[Oo]ff|OFF)$/i, resolve: () => !1, options: n.boolOptions, stringify: w }, { identify: L, default: !0, tag: "tag:yaml.org,2002:int", format: "BIN", test: /^([-+]?)0b([0-1_]+)$/, resolve: ($, z, Z) => C(z, Z, 2), stringify: ($) => A($, 2, "0b") }, { identify: L, default: !0, tag: "tag:yaml.org,2002:int", format: "OCT", test: /^([-+]?)0([0-7_]+)$/, resolve: ($, z, Z) => C(z, Z, 8), stringify: ($) => A($, 8, "0") }, { identify: L, default: !0, tag: "tag:yaml.org,2002:int", test: /^([-+]?)([0-9][0-9_]*)$/, resolve: ($, z, Z) => C(z, Z, 10), stringify: n.stringifyNumber }, { identify: L, default: !0, tag: "tag:yaml.org,2002:int", format: "HEX", test: /^([-+]?)0x([0-9a-fA-F_]+)$/, resolve: ($, z, Z) => C(z, Z, 16), stringify: ($) => A($, 16, "0x") }, { identify: ($) => typeof $ == "number", default: !0, tag: "tag:yaml.org,2002:float", test: /^(?:[-+]?\.inf|(\.nan))$/i, resolve: ($, z) => z ? NaN : $[0] === "-" ? Number.NEGATIVE_INFINITY : Number.POSITIVE_INFINITY, stringify: n.stringifyNumber }, { identify: ($) => typeof $ == "number", default: !0, tag: "tag:yaml.org,2002:float", format: "EXP", test: /^[-+]?([0-9][0-9_]*)?(\.[0-9_]*)?[eE][-+]?[0-9]+$/, resolve: ($) => parseFloat($.replace(/_/g, "")), stringify: ({ value: $ }) => Number($).toExponential() }, { identify: ($) => typeof $ == "number", default: !0, tag: "tag:yaml.org,2002:float", test: /^[-+]?(?:[0-9][0-9_]*)?\.([0-9_]*)$/, resolve($, z) {
    let Z = new n.Scalar(parseFloat($.replace(/_/g, "")));
    if (z) {
      let X = z.replace(/_/g, "");
      X[X.length - 1] === "0" && (Z.minFractionDigits = X.length);
    }
    return Z;
  }, stringify: n.stringifyNumber }], r.binary, r.omap, r.pairs, r.set, r.intTime, r.floatTime, r.timestamp), O = { core: h, failsafe: u, json: E, yaml11: _ }, T = { binary: r.binary, bool: D, float: b, floatExp: y, floatNaN: k, floatTime: r.floatTime, int: x, intHex: N, intOct: S, intTime: r.intTime, map: i, null: v, omap: r.omap, pairs: r.pairs, seq: o, set: r.set, timestamp: r.timestamp };
  function P($, z, Z) {
    if (z) {
      let X = Z.filter((le) => le.tag === z), ne = X.find((le) => !le.format) || X[0];
      if (!ne) throw new Error(`Tag ${z} not found`);
      return ne;
    }
    return Z.find((X) => (X.identify && X.identify($) || X.class && $ instanceof X.class) && !X.format);
  }
  function V($, z, Z) {
    if ($ instanceof n.Node) return $;
    let { defaultPrefix: X, onTagObj: ne, prevObjects: le, schema: nt, wrapScalars: Zt } = Z;
    z && z.startsWith("!!") && (z = X + z.slice(2));
    let en = P($, z, nt.tags);
    if (!en) {
      if (typeof $.toJSON == "function" && ($ = $.toJSON()), !$ || typeof $ != "object") return Zt ? new n.Scalar($) : $;
      en = $ instanceof Map ? i : $[Symbol.iterator] ? o : i;
    }
    ne && (ne(en), delete Z.onTagObj);
    let Vt = { value: void 0, node: void 0 };
    if ($ && typeof $ == "object" && le) {
      let gs = le.get($);
      if (gs) {
        let li = new n.Alias(gs);
        return Z.aliasNodes.push(li), li;
      }
      Vt.value = $, le.set($, Vt);
    }
    return Vt.node = en.createNode ? en.createNode(Z.schema, $, Z) : Zt ? new n.Scalar($) : $, z && Vt.node instanceof n.Node && (Vt.node.tag = z), Vt.node;
  }
  function Y($, z, Z, X) {
    let ne = $[X.replace(/\W/g, "")];
    if (!ne) {
      let le = Object.keys($).map((nt) => JSON.stringify(nt)).join(", ");
      throw new Error(`Unknown schema "${X}"; use one of ${le}`);
    }
    if (Array.isArray(Z)) for (let le of Z) ne = ne.concat(le);
    else typeof Z == "function" && (ne = Z(ne.slice()));
    for (let le = 0; le < ne.length; ++le) {
      let nt = ne[le];
      if (typeof nt == "string") {
        let Zt = z[nt];
        if (!Zt) {
          let en = Object.keys(z).map((Vt) => JSON.stringify(Vt)).join(", ");
          throw new Error(`Unknown custom tag "${nt}"; use one of ${en}`);
        }
        ne[le] = Zt;
      }
    }
    return ne;
  }
  var K = ($, z) => $.key < z.key ? -1 : $.key > z.key ? 1 : 0, J = class xm {
    constructor({ customTags: z, merge: Z, schema: X, sortMapEntries: ne, tags: le }) {
      this.merge = !!Z, this.name = X, this.sortMapEntries = ne === !0 ? K : ne || null, !z && le && r.warnOptionDeprecation("tags", "customTags"), this.tags = Y(O, T, z || le, X);
    }
    createNode(z, Z, X, ne) {
      let le = { defaultPrefix: xm.defaultPrefix, schema: this, wrapScalars: Z }, nt = ne ? Object.assign(ne, le) : le;
      return V(z, X, nt);
    }
    createPair(z, Z, X) {
      X || (X = { wrapScalars: !0 });
      let ne = this.createNode(z, X.wrapScalars, null, X), le = this.createNode(Z, X.wrapScalars, null, X);
      return new n.Pair(ne, le);
    }
  };
  t._defineProperty(J, "defaultPrefix", t.defaultTagPrefix), t._defineProperty(J, "defaultTags", t.defaultTags), e.Schema = J;
}), W2 = pn((e) => {
  var t = fr(), n = ri(), r = Am(), s = { anchorPrefix: "a", customTags: null, indent: 2, indentSeq: !0, keepCstNodes: !1, keepNodeTypes: !0, keepBlobsInJSON: !0, mapAsMap: !1, maxAliasCount: 100, prettyErrors: !1, simpleKeys: !1, version: "1.2" }, i = { get binary() {
    return n.binaryOptions;
  }, set binary(b) {
    Object.assign(n.binaryOptions, b);
  }, get bool() {
    return n.boolOptions;
  }, set bool(b) {
    Object.assign(n.boolOptions, b);
  }, get int() {
    return n.intOptions;
  }, set int(b) {
    Object.assign(n.intOptions, b);
  }, get null() {
    return n.nullOptions;
  }, set null(b) {
    Object.assign(n.nullOptions, b);
  }, get str() {
    return n.strOptions;
  }, set str(b) {
    Object.assign(n.strOptions, b);
  } }, a = { "1.0": { schema: "yaml-1.1", merge: !0, tagPrefixes: [{ handle: "!", prefix: t.defaultTagPrefix }, { handle: "!!", prefix: "tag:private.yaml.org,2002:" }] }, 1.1: { schema: "yaml-1.1", merge: !0, tagPrefixes: [{ handle: "!", prefix: "!" }, { handle: "!!", prefix: t.defaultTagPrefix }] }, 1.2: { schema: "core", merge: !1, tagPrefixes: [{ handle: "!", prefix: "!" }, { handle: "!!", prefix: t.defaultTagPrefix }] } };
  function o(b, h) {
    if ((b.version || b.options.version) === "1.0") {
      let E = h.match(/^tag:private\.yaml\.org,2002:([^:/]+)$/);
      if (E) return "!" + E[1];
      let w = h.match(/^tag:([a-zA-Z0-9-]+)\.yaml\.org,2002:(.*)/);
      return w ? `!${w[1]}/${w[2]}` : `!${h.replace(/^tag:/, "")}`;
    }
    let m = b.tagPrefixes.find((E) => h.indexOf(E.prefix) === 0);
    if (!m) {
      let E = b.getDefaults().tagPrefixes;
      m = E && E.find((w) => h.indexOf(w.prefix) === 0);
    }
    if (!m) return h[0] === "!" ? h : `!<${h}>`;
    let p = h.substr(m.prefix.length).replace(/[!,[\]{}]/g, (E) => ({ "!": "%21", ",": "%2C", "[": "%5B", "]": "%5D", "{": "%7B", "}": "%7D" })[E]);
    return m.handle + p;
  }
  function l(b, h) {
    if (h instanceof n.Alias) return n.Alias;
    if (h.tag) {
      let E = b.filter((w) => w.tag === h.tag);
      if (E.length > 0) return E.find((w) => w.format === h.format) || E[0];
    }
    let m, p;
    if (h instanceof n.Scalar) {
      p = h.value;
      let E = b.filter((w) => w.identify && w.identify(p) || w.class && p instanceof w.class);
      m = E.find((w) => w.format === h.format) || E.find((w) => !w.format);
    } else p = h, m = b.find((E) => E.nodeClass && p instanceof E.nodeClass);
    if (!m) {
      let E = p && p.constructor ? p.constructor.name : typeof p;
      throw new Error(`Tag not resolved for ${E} value`);
    }
    return m;
  }
  function u(b, h, { anchors: m, doc: p }) {
    let E = [], w = p.anchors.getName(b);
    return w && (m[w] = b, E.push(`&${w}`)), b.tag ? E.push(o(p, b.tag)) : h.default || E.push(o(p, h.tag)), E.join(" ");
  }
  function f(b, h, m, p) {
    let { anchors: E, schema: w } = h.doc, L;
    if (!(b instanceof n.Node)) {
      let _ = { aliasNodes: [], onTagObj: (O) => L = O, prevObjects: /* @__PURE__ */ new Map() };
      b = w.createNode(b, !0, null, _);
      for (let O of _.aliasNodes) {
        O.source = O.source.node;
        let T = E.getName(O.source);
        T || (T = E.newName(), E.map[T] = O.source);
      }
    }
    if (b instanceof n.Pair) return b.toString(h, m, p);
    L || (L = l(w.tags, b));
    let C = u(b, L, h);
    C.length > 0 && (h.indentAtStart = (h.indentAtStart || 0) + C.length + 1);
    let A = typeof L.stringify == "function" ? L.stringify(b, h, m, p) : b instanceof n.Scalar ? n.stringifyString(b, h, m, p) : b.toString(h, m, p);
    return C ? b instanceof n.Scalar || A[0] === "{" || A[0] === "[" ? `${C} ${A}` : `${C}
${h.indent}${A}` : A;
  }
  var c = class Nm {
    static validAnchorNode(h) {
      return h instanceof n.Scalar || h instanceof n.YAMLSeq || h instanceof n.YAMLMap;
    }
    constructor(h) {
      t._defineProperty(this, "map", /* @__PURE__ */ Object.create(null)), this.prefix = h;
    }
    createAlias(h, m) {
      return this.setAnchor(h, m), new n.Alias(h);
    }
    createMergePair(...h) {
      let m = new n.Merge();
      return m.value.items = h.map((p) => {
        if (p instanceof n.Alias) {
          if (p.source instanceof n.YAMLMap) return p;
        } else if (p instanceof n.YAMLMap) return this.createAlias(p);
        throw new Error("Merge sources must be Map nodes or their Aliases");
      }), m;
    }
    getName(h) {
      let { map: m } = this;
      return Object.keys(m).find((p) => m[p] === h);
    }
    getNames() {
      return Object.keys(this.map);
    }
    getNode(h) {
      return this.map[h];
    }
    newName(h) {
      h || (h = this.prefix);
      let m = Object.keys(this.map);
      for (let p = 1; ; ++p) {
        let E = `${h}${p}`;
        if (!m.includes(E)) return E;
      }
    }
    resolveNodes() {
      let { map: h, _cstAliases: m } = this;
      Object.keys(h).forEach((p) => {
        h[p] = h[p].resolved;
      }), m.forEach((p) => {
        p.source = p.source.resolved;
      }), delete this._cstAliases;
    }
    setAnchor(h, m) {
      if (h != null && !Nm.validAnchorNode(h)) throw new Error("Anchors may only be set for Scalar, Seq and Map nodes");
      if (m && /[\x00-\x19\s,[\]{}]/.test(m)) throw new Error("Anchor names must not contain whitespace or control characters");
      let { map: p } = this, E = h && Object.keys(p).find((w) => p[w] === h);
      if (E) if (m) E !== m && (delete p[E], p[m] = h);
      else return E;
      else {
        if (!m) {
          if (!h) return null;
          m = this.newName();
        }
        p[m] = h;
      }
      return m;
    }
  }, d = (b, h) => {
    if (b && typeof b == "object") {
      let { tag: m } = b;
      b instanceof n.Collection ? (m && (h[m] = !0), b.items.forEach((p) => d(p, h))) : b instanceof n.Pair ? (d(b.key, h), d(b.value, h)) : b instanceof n.Scalar && m && (h[m] = !0);
    }
    return h;
  }, v = (b) => Object.keys(d(b, {}));
  function D(b, h) {
    let m = { before: [], after: [] }, p, E = !1;
    for (let w of h) if (w.valueRange) {
      if (p !== void 0) {
        let C = "Document contains trailing content not separated by a ... or --- line";
        b.errors.push(new t.YAMLSyntaxError(w, C));
        break;
      }
      let L = n.resolveNode(b, w);
      E && (L.spaceBefore = !0, E = !1), p = L;
    } else w.comment !== null ? (p === void 0 ? m.before : m.after).push(w.comment) : w.type === t.Type.BLANK_LINE && (E = !0, p === void 0 && m.before.length > 0 && !b.commentBefore && (b.commentBefore = m.before.join(`
`), m.before = []));
    if (b.contents = p || null, !p) b.comment = m.before.concat(m.after).join(`
`) || null;
    else {
      let w = m.before.join(`
`);
      if (w) {
        let L = p instanceof n.Collection && p.items[0] ? p.items[0] : p;
        L.commentBefore = L.commentBefore ? `${w}
${L.commentBefore}` : w;
      }
      b.comment = m.after.join(`
`) || null;
    }
  }
  function S({ tagPrefixes: b }, h) {
    let [m, p] = h.parameters;
    if (!m || !p) {
      let E = "Insufficient parameters given for %TAG directive";
      throw new t.YAMLSemanticError(h, E);
    }
    if (b.some((E) => E.handle === m)) {
      let E = "The %TAG directive must only be given at most once per handle in the same document.";
      throw new t.YAMLSemanticError(h, E);
    }
    return { handle: m, prefix: p };
  }
  function x(b, h) {
    let [m] = h.parameters;
    if (h.name === "YAML:1.0" && (m = "1.0"), !m) {
      let p = "Insufficient parameters given for %YAML directive";
      throw new t.YAMLSemanticError(h, p);
    }
    if (!a[m]) {
      let p = `Document will be parsed as YAML ${b.version || b.options.version} rather than YAML ${m}`;
      b.warnings.push(new t.YAMLWarning(h, p));
    }
    return m;
  }
  function N(b, h, m) {
    let p = [], E = !1;
    for (let w of h) {
      let { comment: L, name: C } = w;
      switch (C) {
        case "TAG":
          try {
            b.tagPrefixes.push(S(b, w));
          } catch (A) {
            b.errors.push(A);
          }
          E = !0;
          break;
        case "YAML":
        case "YAML:1.0":
          if (b.version) {
            let A = "The %YAML directive must only be given at most once per document.";
            b.errors.push(new t.YAMLSemanticError(w, A));
          }
          try {
            b.version = x(b, w);
          } catch (A) {
            b.errors.push(A);
          }
          E = !0;
          break;
        default:
          if (C) {
            let A = `YAML only supports %TAG and %YAML directives, and not %${C}`;
            b.warnings.push(new t.YAMLWarning(w, A));
          }
      }
      L && p.push(L);
    }
    if (m && !E && (b.version || m.version || b.options.version) === "1.1") {
      let w = ({ handle: L, prefix: C }) => ({ handle: L, prefix: C });
      b.tagPrefixes = m.tagPrefixes.map(w), b.version = m.version;
    }
    b.commentBefore = p.join(`
`) || null;
  }
  function k(b) {
    if (b instanceof n.Collection) return !0;
    throw new Error("Expected a YAML collection as document contents");
  }
  var y = class Tl {
    constructor(h) {
      this.anchors = new c(h.anchorPrefix), this.commentBefore = null, this.comment = null, this.contents = null, this.directivesEndMarker = null, this.errors = [], this.options = h, this.schema = null, this.tagPrefixes = [], this.version = null, this.warnings = [];
    }
    add(h) {
      return k(this.contents), this.contents.add(h);
    }
    addIn(h, m) {
      k(this.contents), this.contents.addIn(h, m);
    }
    delete(h) {
      return k(this.contents), this.contents.delete(h);
    }
    deleteIn(h) {
      return n.isEmptyPath(h) ? this.contents == null ? !1 : (this.contents = null, !0) : (k(this.contents), this.contents.deleteIn(h));
    }
    getDefaults() {
      return Tl.defaults[this.version] || Tl.defaults[this.options.version] || {};
    }
    get(h, m) {
      return this.contents instanceof n.Collection ? this.contents.get(h, m) : void 0;
    }
    getIn(h, m) {
      return n.isEmptyPath(h) ? !m && this.contents instanceof n.Scalar ? this.contents.value : this.contents : this.contents instanceof n.Collection ? this.contents.getIn(h, m) : void 0;
    }
    has(h) {
      return this.contents instanceof n.Collection ? this.contents.has(h) : !1;
    }
    hasIn(h) {
      return n.isEmptyPath(h) ? this.contents !== void 0 : this.contents instanceof n.Collection ? this.contents.hasIn(h) : !1;
    }
    set(h, m) {
      k(this.contents), this.contents.set(h, m);
    }
    setIn(h, m) {
      n.isEmptyPath(h) ? this.contents = m : (k(this.contents), this.contents.setIn(h, m));
    }
    setSchema(h, m) {
      if (!h && !m && this.schema) return;
      typeof h == "number" && (h = h.toFixed(1)), h === "1.0" || h === "1.1" || h === "1.2" ? (this.version ? this.version = h : this.options.version = h, delete this.options.schema) : h && typeof h == "string" && (this.options.schema = h), Array.isArray(m) && (this.options.customTags = m);
      let p = Object.assign({}, this.getDefaults(), this.options);
      this.schema = new r.Schema(p);
    }
    parse(h, m) {
      this.options.keepCstNodes && (this.cstNode = h), this.options.keepNodeTypes && (this.type = "DOCUMENT");
      let { directives: p = [], contents: E = [], directivesEndMarker: w, error: L, valueRange: C } = h;
      if (L && (L.source || (L.source = this), this.errors.push(L)), N(this, p, m), w && (this.directivesEndMarker = !0), this.range = C ? [C.start, C.end] : null, this.setSchema(), this.anchors._cstAliases = [], D(this, E), this.anchors.resolveNodes(), this.options.prettyErrors) {
        for (let A of this.errors) A instanceof t.YAMLError && A.makePretty();
        for (let A of this.warnings) A instanceof t.YAMLError && A.makePretty();
      }
      return this;
    }
    listNonDefaultTags() {
      return v(this.contents).filter((h) => h.indexOf(r.Schema.defaultPrefix) !== 0);
    }
    setTagPrefix(h, m) {
      if (h[0] !== "!" || h[h.length - 1] !== "!") throw new Error("Handle must start and end with !");
      if (m) {
        let p = this.tagPrefixes.find((E) => E.handle === h);
        p ? p.prefix = m : this.tagPrefixes.push({ handle: h, prefix: m });
      } else this.tagPrefixes = this.tagPrefixes.filter((p) => p.handle !== h);
    }
    toJSON(h, m) {
      let { keepBlobsInJSON: p, mapAsMap: E, maxAliasCount: w } = this.options, L = p && (typeof h != "string" || !(this.contents instanceof n.Scalar)), C = { doc: this, indentStep: "  ", keep: L, mapAsMap: L && !!E, maxAliasCount: w, stringify: f }, A = Object.keys(this.anchors.map);
      A.length > 0 && (C.anchors = new Map(A.map((O) => [this.anchors.map[O], { alias: [], aliasCount: 0, count: 1 }])));
      let _ = n.toJSON(this.contents, h, C);
      if (typeof m == "function" && C.anchors) for (let { count: O, res: T } of C.anchors.values()) m(T, O);
      return _;
    }
    toString() {
      if (this.errors.length > 0) throw new Error("Document with errors cannot be stringified");
      let h = this.options.indent;
      if (!Number.isInteger(h) || h <= 0) {
        let A = JSON.stringify(h);
        throw new Error(`"indent" option must be a positive integer, not ${A}`);
      }
      this.setSchema();
      let m = [], p = !1;
      if (this.version) {
        let A = "%YAML 1.2";
        this.schema.name === "yaml-1.1" && (this.version === "1.0" ? A = "%YAML:1.0" : this.version === "1.1" && (A = "%YAML 1.1")), m.push(A), p = !0;
      }
      let E = this.listNonDefaultTags();
      this.tagPrefixes.forEach(({ handle: A, prefix: _ }) => {
        E.some((O) => O.indexOf(_) === 0) && (m.push(`%TAG ${A} ${_}`), p = !0);
      }), (p || this.directivesEndMarker) && m.push("---"), this.commentBefore && ((p || !this.directivesEndMarker) && m.unshift(""), m.unshift(this.commentBefore.replace(/^/gm, "#")));
      let w = { anchors: /* @__PURE__ */ Object.create(null), doc: this, indent: "", indentStep: " ".repeat(h), stringify: f }, L = !1, C = null;
      if (this.contents) {
        this.contents instanceof n.Node && (this.contents.spaceBefore && (p || this.directivesEndMarker) && m.push(""), this.contents.commentBefore && m.push(this.contents.commentBefore.replace(/^/gm, "#")), w.forceBlockIndent = !!this.comment, C = this.contents.comment);
        let A = C ? null : () => L = !0, _ = f(this.contents, w, () => C = null, A);
        m.push(n.addComment(_, "", C));
      } else this.contents !== void 0 && m.push(f(this.contents, w));
      return this.comment && ((!L || C) && m[m.length - 1] !== "" && m.push(""), m.push(this.comment.replace(/^/gm, "#"))), m.join(`
`) + `
`;
    }
  };
  t._defineProperty(y, "defaults", a), e.Document = y, e.defaultOptions = s, e.scalarOptions = i;
}), H2 = pn((e) => {
  var t = q2(), n = W2(), r = Am(), s = fr(), i = Dm();
  ri();
  function a(v, D = !0, S) {
    S === void 0 && typeof D == "string" && (S = D, D = !0);
    let x = Object.assign({}, n.Document.defaults[n.defaultOptions.version], n.defaultOptions);
    return new r.Schema(x).createNode(v, D, S);
  }
  var o = class extends n.Document {
    constructor(v) {
      super(Object.assign({}, n.defaultOptions, v));
    }
  };
  function l(v, D) {
    let S = [], x;
    for (let N of t.parse(v)) {
      let k = new o(D);
      k.parse(N, x), S.push(k), x = k;
    }
    return S;
  }
  function u(v, D) {
    let S = t.parse(v), x = new o(D).parse(S[0]);
    if (S.length > 1) {
      let N = "Source contains multiple documents; please use YAML.parseAllDocuments()";
      x.errors.unshift(new s.YAMLSemanticError(S[1], N));
    }
    return x;
  }
  function f(v, D) {
    let S = u(v, D);
    if (S.warnings.forEach((x) => i.warn(x)), S.errors.length > 0) throw S.errors[0];
    return S.toJSON();
  }
  function c(v, D) {
    let S = new o(D);
    return S.contents = v, String(S);
  }
  var d = { createNode: a, defaultOptions: n.defaultOptions, Document: o, parse: f, parseAllDocuments: l, parseCST: t.parse, parseDocument: u, scalarOptions: n.scalarOptions, stringify: c };
  e.YAML = d;
}), Lm = pn((e, t) => {
  t.exports = H2().YAML;
}), Y2 = pn((e) => {
  var t = ri(), n = fr();
  e.findPair = t.findPair, e.parseMap = t.resolveMap, e.parseSeq = t.resolveSeq, e.stringifyNumber = t.stringifyNumber, e.stringifyString = t.stringifyString, e.toJSON = t.toJSON, e.Type = n.Type, e.YAMLError = n.YAMLError, e.YAMLReferenceError = n.YAMLReferenceError, e.YAMLSemanticError = n.YAMLSemanticError, e.YAMLSyntaxError = n.YAMLSyntaxError, e.YAMLWarning = n.YAMLWarning;
}), km = {};
mm(km, { __parsePrettierYamlConfig: () => hp, languages: () => Qm, options: () => Km, parsers: () => _u, printers: () => fp });
var z2 = (e, t, n, r) => {
  if (!(e && t == null)) return t.replaceAll ? t.replaceAll(n, r) : n.global ? t.replace(n, r) : t.split(n).join(r);
}, uo = z2, Cm = "string", Fm = "array", _m = "cursor", Tm = "indent", Au = "align", Mm = "trim", xu = "group", Nu = "fill", Lu = "if-break", Om = "indent-if-break", ku = "line-suffix", Rm = "line-suffix-boundary", hs = "line", Pm = "label", Cu = "break-parent", Im = /* @__PURE__ */ new Set([_m, Tm, Au, Mm, xu, Nu, Lu, Om, ku, Rm, hs, Pm, Cu]), G2 = (e, t, n) => {
  if (!(e && t == null)) return Array.isArray(t) || typeof t == "string" ? t[n < 0 ? t.length + n : n] : t.at(n);
}, Nt = G2;
function J2(e) {
  if (typeof e == "string") return Cm;
  if (Array.isArray(e)) return Fm;
  if (!e) return;
  let { type: t } = e;
  if (Im.has(t)) return t;
}
var $m = J2, Q2 = (e) => new Intl.ListFormat("en-US", { type: "disjunction" }).format(e);
function K2(e) {
  let t = e === null ? "null" : typeof e;
  if (t !== "string" && t !== "object") return `Unexpected doc '${t}', 
Expected it to be 'string' or 'object'.`;
  if ($m(e)) throw new Error("doc is valid.");
  let n = Object.prototype.toString.call(e);
  if (n !== "[object Object]") return `Unexpected doc '${n}'.`;
  let r = Q2([...Im].map((s) => `'${s}'`));
  return `Unexpected doc.type '${e.type}'.
Expected it to be ${r}.`;
}
var X2 = class extends Error {
  name = "InvalidDocError";
  constructor(t) {
    super(K2(t)), this.doc = t;
  }
}, Z2 = X2;
function ev(e, t) {
  if (typeof e == "string") return t(e);
  let n = /* @__PURE__ */ new Map();
  return r(e);
  function r(i) {
    if (n.has(i)) return n.get(i);
    let a = s(i);
    return n.set(i, a), a;
  }
  function s(i) {
    switch ($m(i)) {
      case Fm:
        return t(i.map(r));
      case Nu:
        return t({ ...i, parts: i.parts.map(r) });
      case Lu:
        return t({ ...i, breakContents: r(i.breakContents), flatContents: r(i.flatContents) });
      case xu: {
        let { expandedStates: a, contents: o } = i;
        return a ? (a = a.map(r), o = a[0]) : o = r(o), t({ ...i, contents: o, expandedStates: a });
      }
      case Au:
      case Tm:
      case Om:
      case Pm:
      case ku:
        return t({ ...i, contents: r(i.contents) });
      case Cm:
      case _m:
      case Mm:
      case Rm:
      case hs:
      case Cu:
        return t(i);
      default:
        throw new Z2(i);
    }
  }
}
function tv(e, t = Ol) {
  return ev(e, (n) => typeof n == "string" ? ut(t, n.split(`
`)) : n);
}
var nv = () => {
}, rv = nv;
function Oa(e, t) {
  return { type: Au, contents: t, n: e };
}
function ca(e, t = {}) {
  return rv(t.expandedStates), { type: xu, id: t.id, contents: e, break: !!t.shouldBreak, expandedStates: t.expandedStates };
}
function Kh(e) {
  return Oa(Number.NEGATIVE_INFINITY, e);
}
function sv(e) {
  return Oa({ type: "root" }, e);
}
function iv(e) {
  return Oa(-1, e);
}
function Xh(e, t) {
  return ca(e[0], { ...t, expandedStates: e });
}
function Bm(e) {
  return { type: Nu, parts: e };
}
function Ml(e, t = "", n = {}) {
  return { type: Lu, breakContents: e, flatContents: t, groupId: n.groupId };
}
function av(e) {
  return { type: ku, contents: e };
}
var Fu = { type: Cu }, ov = { type: hs, hard: !0 }, lv = { type: hs, hard: !0, literal: !0 }, si = { type: hs }, Vm = { type: hs, soft: !0 }, ve = [ov, Fu], Ol = [lv, Fu];
function ut(e, t) {
  let n = [];
  for (let r = 0; r < t.length; r++) r !== 0 && n.push(e), n.push(t[r]);
  return n;
}
function uv(e) {
  return (t, n, r) => {
    let s = !!(r != null && r.backwards);
    if (n === !1) return !1;
    let { length: i } = t, a = n;
    for (; a >= 0 && a < i; ) {
      let o = t.charAt(a);
      if (e instanceof RegExp) {
        if (!e.test(o)) return a;
      } else if (!e.includes(o)) return a;
      s ? a-- : a++;
    }
    return a === -1 || a === i ? a : !1;
  };
}
var Zh = uv(" 	");
function cv(e, t, n) {
  let r = !!(n != null && n.backwards);
  if (t === !1) return !1;
  let s = e.charAt(t);
  if (r) {
    if (e.charAt(t - 1) === "\r" && s === `
`) return t - 2;
    if (s === `
` || s === "\r" || s === "\u2028" || s === "\u2029") return t - 1;
  } else {
    if (s === "\r" && e.charAt(t + 1) === `
`) return t + 2;
    if (s === `
` || s === "\r" || s === "\u2028" || s === "\u2029") return t + 1;
  }
  return t;
}
var ed = cv;
function fv(e, t) {
  let n = t - 1;
  n = Zh(e, n, { backwards: !0 }), n = ed(e, n, { backwards: !0 }), n = Zh(e, n, { backwards: !0 });
  let r = ed(e, n, { backwards: !0 });
  return n !== r;
}
var hv = fv, dv = class extends Error {
  name = "UnexpectedNodeError";
  constructor(t, n, r = "type") {
    super(`Unexpected ${n} node ${r}: ${JSON.stringify(t[r])}.`), this.node = t;
  }
}, mv = dv;
function jm(e, t) {
  let { node: n } = e;
  if (n.type === "root" && t.filepath && /(?:[/\\]|^)\.(?:prettier|stylelint|lintstaged)rc$/u.test(t.filepath)) return async (r) => {
    let s = await r(t.originalText, { parser: "json" });
    return s ? [s, ve] : void 0;
  };
}
jm.getVisitorKeys = () => [];
var pv = jm, Ss = null;
function Is(e) {
  if (Ss !== null && typeof Ss.property) {
    let t = Ss;
    return Ss = Is.prototype = null, t;
  }
  return Ss = Is.prototype = e ?? /* @__PURE__ */ Object.create(null), new Is();
}
var gv = 10;
for (let e = 0; e <= gv; e++) Is();
function yv(e) {
  return Is(e);
}
function bv(e, t = "type") {
  yv(e);
  function n(r) {
    let s = r[t], i = e[s];
    if (!Array.isArray(i)) throw Object.assign(new Error(`Missing visitor keys for '${s}'.`), { node: r });
    return i;
  }
  return n;
}
var vv = bv, wv = Object.fromEntries(Object.entries({ root: ["children"], document: ["head", "body", "children"], documentHead: ["children"], documentBody: ["children"], directive: [], alias: [], blockLiteral: [], blockFolded: ["children"], plain: ["children"], quoteSingle: [], quoteDouble: [], mapping: ["children"], mappingItem: ["key", "value", "children"], mappingKey: ["content", "children"], mappingValue: ["content", "children"], sequence: ["children"], sequenceItem: ["content", "children"], flowMapping: ["children"], flowMappingItem: ["key", "value", "children"], flowSequence: ["children"], flowSequenceItem: ["content", "children"], comment: [], tag: [], anchor: [] }).map(([e, t]) => [e, [...t, "anchor", "tag", "indicatorComment", "leadingComments", "middleComments", "trailingComment", "endComments"]])), Dv = wv, Sv = vv(Dv), Ev = Sv;
function fa(e) {
  return e.position.start.offset;
}
function Av(e) {
  return e.position.end.offset;
}
var xv = "format", Nv = /^\s*#[^\S\n]*@(?:noformat|noprettier)\s*?(?:\n|$)/u, Lv = /^\s*#[^\S\n]*@(?:format|prettier)\s*?(?:\n|$)/u, kv = /^\s*@(?:format|prettier)\s*$/u;
function Cv(e) {
  return kv.test(e);
}
function Fv(e) {
  return Lv.test(e);
}
function _v(e) {
  return Nv.test(e);
}
function Tv(e) {
  return `# @${xv}

${e}`;
}
function Mv(e) {
  return Array.isArray(e) && e.length > 0;
}
var ii = Mv;
function Gt(e, t) {
  return typeof e?.type == "string" && (!t || t.includes(e.type));
}
function Um(e, t, n) {
  return t("children" in e ? { ...e, children: e.children.map((r) => Um(r, t, e)) } : e, n);
}
function Es(e, t, n) {
  Object.defineProperty(e, t, { get: n, enumerable: !1 });
}
function Ov(e, t) {
  let n = 0, r = t.length;
  for (let s = e.position.end.offset - 1; s < r; s++) {
    let i = t[s];
    if (i === `
` && n++, n === 1 && /\S/u.test(i)) return !1;
    if (n === 2) return !0;
  }
  return !1;
}
function qm(e) {
  let { node: t } = e;
  switch (t.type) {
    case "tag":
    case "anchor":
    case "comment":
      return !1;
  }
  let n = e.stack.length;
  for (let r = 1; r < n; r++) {
    let s = e.stack[r], i = e.stack[r - 1];
    if (Array.isArray(i) && typeof s == "number" && s !== i.length - 1) return !1;
  }
  return !0;
}
function Rl(e) {
  return ii(e.children) ? Rl(Nt(!1, e.children, -1)) : e;
}
function td(e) {
  return e.value.trim() === "prettier-ignore";
}
function Rv(e) {
  let { node: t } = e;
  if (t.type === "documentBody") {
    let n = e.parent.head;
    return Lt(n) && td(Nt(!1, n.endComments, -1));
  }
  return Fn(t) && td(Nt(!1, t.leadingComments, -1));
}
function ha(e) {
  return !ii(e.children) && !Pv(e);
}
function Pv(e) {
  return Fn(e) || Gr(e) || Wm(e) || Pt(e) || Lt(e);
}
function Fn(e) {
  return ii(e?.leadingComments);
}
function Gr(e) {
  return ii(e?.middleComments);
}
function Wm(e) {
  return e?.indicatorComment;
}
function Pt(e) {
  return e?.trailingComment;
}
function Lt(e) {
  return ii(e?.endComments);
}
function Hm(e) {
  let t = [], n;
  for (let r of e.split(/( +)/u)) r !== " " ? n === " " ? t.push(r) : t.push((t.pop() || "") + r) : n === void 0 && t.unshift(""), n = r;
  return n === " " && t.push((t.pop() || "") + " "), t[0] === "" && (t.shift(), t.unshift(" " + (t.shift() || ""))), t;
}
function Iv(e, t, n) {
  let r = t.split(`
`).map((s, i, a) => i === 0 && i === a.length - 1 ? s : i !== 0 && i !== a.length - 1 ? s.trim() : i === 0 ? s.trimEnd() : s.trimStart());
  return n.proseWrap === "preserve" ? r.map((s) => s.length === 0 ? [] : [s]) : r.map((s) => s.length === 0 ? [] : Hm(s)).reduce((s, i, a) => a !== 0 && r[a - 1].length > 0 && i.length > 0 && !(e === "quoteDouble" && Nt(!1, Nt(!1, s, -1), -1).endsWith("\\")) ? [...s.slice(0, -1), [...Nt(!1, s, -1), ...i]] : [...s, i], []).map((s) => n.proseWrap === "never" ? [s.join(" ")] : s);
}
function $v(e, { parentIndent: t, isLastDescendant: n, options: r }) {
  let s = e.position.start.line === e.position.end.line ? "" : r.originalText.slice(e.position.start.offset, e.position.end.offset).match(/^[^\n]*\n(.*)$/su)[1], i;
  if (e.indent === null) {
    let l = s.match(/^(?<leadingSpace> *)[^\n\r ]/mu);
    i = l ? l.groups.leadingSpace.length : Number.POSITIVE_INFINITY;
  } else i = e.indent - 1 + t;
  let a = s.split(`
`).map((l) => l.slice(i));
  if (r.proseWrap === "preserve" || e.type === "blockLiteral") return o(a.map((l) => l.length === 0 ? [] : [l]));
  return o(a.map((l) => l.length === 0 ? [] : Hm(l)).reduce((l, u, f) => f !== 0 && a[f - 1].length > 0 && u.length > 0 && !/^\s/u.test(u[0]) && !/^\s|\s$/u.test(Nt(!1, l, -1)) ? [...l.slice(0, -1), [...Nt(!1, l, -1), ...u]] : [...l, u], []).map((l) => l.reduce((u, f) => u.length > 0 && /\s$/u.test(Nt(!1, u, -1)) ? [...u.slice(0, -1), Nt(!1, u, -1) + " " + f] : [...u, f], [])).map((l) => r.proseWrap === "never" ? [l.join(" ")] : l));
  function o(l) {
    if (e.chomping === "keep") return Nt(!1, l, -1).length === 0 ? l.slice(0, -1) : l;
    let u = 0;
    for (let f = l.length - 1; f >= 0 && l[f].length === 0; f--) u++;
    return u === 0 ? l : u >= 2 && !n ? l.slice(0, -(u - 1)) : l.slice(0, -u);
  }
}
function Pl(e) {
  if (!e) return !0;
  switch (e.type) {
    case "plain":
    case "quoteDouble":
    case "quoteSingle":
    case "alias":
    case "flowMapping":
    case "flowSequence":
      return !0;
    default:
      return !1;
  }
}
var co = /* @__PURE__ */ new WeakMap();
function Ym(e, t) {
  let { node: n, root: r } = e, s;
  return co.has(r) ? s = co.get(r) : (s = /* @__PURE__ */ new Set(), co.set(r, s)), !s.has(n.position.end.line) && (s.add(n.position.end.line), Ov(n, t) && !zm(e.parent)) ? Vm : "";
}
function zm(e) {
  return Lt(e) && !Gt(e, ["documentHead", "documentBody", "flowMapping", "flowSequence"]);
}
function Dt(e, t) {
  return Oa(" ".repeat(e), t);
}
function Bv(e, t, n) {
  let { node: r } = e, s = e.ancestors.filter((u) => u.type === "sequence" || u.type === "mapping").length, i = qm(e), a = [r.type === "blockFolded" ? ">" : "|"];
  r.indent !== null && a.push(r.indent.toString()), r.chomping !== "clip" && a.push(r.chomping === "keep" ? "+" : "-"), Wm(r) && a.push(" ", n("indicatorComment"));
  let o = $v(r, { parentIndent: s, isLastDescendant: i, options: t }), l = [];
  for (let [u, f] of o.entries()) u === 0 && l.push(ve), l.push(Bm(ut(si, f))), u !== o.length - 1 ? l.push(f.length === 0 ? ve : sv(Ol)) : r.chomping === "keep" && i && l.push(Kh(f.length === 0 ? ve : Ol));
  return r.indent === null ? a.push(iv(Dt(t.tabWidth, l))) : a.push(Kh(Dt(r.indent - 1 + s, l))), a;
}
var Vv = Bv;
function nd(e, t, n) {
  let { node: r } = e, s = r.type === "flowMapping", i = s ? "{" : "[", a = s ? "}" : "]", o = Vm;
  s && r.children.length > 0 && t.bracketSpacing && (o = si);
  let l = Nt(!1, r.children, -1), u = l?.type === "flowMappingItem" && ha(l.key) && ha(l.value);
  return [i, Dt(t.tabWidth, [o, jv(e, t, n), t.trailingComma === "none" ? "" : Ml(","), Lt(r) ? [ve, ut(ve, e.map(n, "endComments"))] : ""]), u ? "" : o, a];
}
function jv(e, t, n) {
  return e.map(({ isLast: r, node: s, next: i }) => [n(), r ? "" : [",", si, s.position.start.line !== i.position.start.line ? Ym(e, t.originalText) : ""]], "children");
}
function Uv(e, t, n) {
  var r;
  let { node: s, parent: i } = e, { key: a, value: o } = s, l = ha(a), u = ha(o);
  if (l && u) return ": ";
  let f = n("key"), c = qv(s) ? " " : "";
  if (u) return s.type === "flowMappingItem" && i.type === "flowMapping" ? f : s.type === "mappingItem" && fo(a.content, t) && !Pt(a.content) && ((r = i.tag) == null ? void 0 : r.value) !== "tag:yaml.org,2002:set" ? [f, c, ":"] : ["? ", Dt(2, f)];
  let d = n("value");
  if (l) return [": ", Dt(2, d)];
  if (Fn(o) || !Pl(a.content)) return ["? ", Dt(2, f), ve, ...e.map(() => [n(), ve], "value", "leadingComments"), ": ", Dt(2, d)];
  if (Wv(a.content) && !Fn(a.content) && !Gr(a.content) && !Pt(a.content) && !Lt(a) && !Fn(o.content) && !Gr(o.content) && !Lt(o) && fo(o.content, t)) return [f, c, ": ", d];
  let v = Symbol("mappingKey"), D = ca([Ml("? "), ca(Dt(2, f), { id: v })]), S = [ve, ": ", Dt(2, d)], x = [c, ":"];
  Lt(o) && o.content && Gt(o.content, ["flowMapping", "flowSequence"]) && o.content.children.length === 0 ? x.push(" ") : Fn(o.content) || Lt(o) && o.content && !Gt(o.content, ["mapping", "sequence"]) || i.type === "mapping" && Pt(a.content) && Pl(o.content) || Gt(o.content, ["mapping", "sequence"]) && o.content.tag === null && o.content.anchor === null ? x.push(ve) : o.content ? x.push(si) : Pt(o) && x.push(" "), x.push(d);
  let N = Dt(t.tabWidth, x);
  return fo(a.content, t) && !Fn(a.content) && !Gr(a.content) && !Lt(a) ? Xh([[f, N]]) : Xh([[D, Ml(S, N, { groupId: v })]]);
}
function fo(e, t) {
  if (!e) return !0;
  switch (e.type) {
    case "plain":
    case "quoteSingle":
    case "quoteDouble":
      break;
    case "alias":
      return !0;
    default:
      return !1;
  }
  if (t.proseWrap === "preserve") return e.position.start.line === e.position.end.line;
  if (/\\$/mu.test(t.originalText.slice(e.position.start.offset, e.position.end.offset))) return !1;
  switch (t.proseWrap) {
    case "never":
      return !e.value.includes(`
`);
    case "always":
      return !/[\n ]/u.test(e.value);
    default:
      return !1;
  }
}
function qv(e) {
  var t;
  return ((t = e.key.content) == null ? void 0 : t.type) === "alias";
}
function Wv(e) {
  if (!e) return !0;
  switch (e.type) {
    case "plain":
    case "quoteDouble":
    case "quoteSingle":
      return e.position.start.line === e.position.end.line;
    case "alias":
      return !0;
    default:
      return !1;
  }
}
var Hv = Uv;
function Yv(e) {
  return Um(e, zv);
}
function zv(e) {
  switch (e.type) {
    case "document":
      Es(e, "head", () => e.children[0]), Es(e, "body", () => e.children[1]);
      break;
    case "documentBody":
    case "sequenceItem":
    case "flowSequenceItem":
    case "mappingKey":
    case "mappingValue":
      Es(e, "content", () => e.children[0]);
      break;
    case "mappingItem":
    case "flowMappingItem":
      Es(e, "key", () => e.children[0]), Es(e, "value", () => e.children[1]);
      break;
  }
  return e;
}
var Gv = Yv;
function Jv(e, t, n) {
  let { node: r } = e, s = [];
  r.type !== "mappingValue" && Fn(r) && s.push([ut(ve, e.map(n, "leadingComments")), ve]);
  let { tag: i, anchor: a } = r;
  i && s.push(n("tag")), i && a && s.push(" "), a && s.push(n("anchor"));
  let o = "";
  return Gt(r, ["mapping", "sequence", "comment", "directive", "mappingItem", "sequenceItem"]) && !qm(e) && (o = Ym(e, t.originalText)), (i || a) && (Gt(r, ["sequence", "mapping"]) && !Gr(r) ? s.push(ve) : s.push(" ")), Gr(r) && s.push([r.middleComments.length === 1 ? "" : ve, ut(ve, e.map(n, "middleComments")), ve]), Rv(e) ? s.push(tv(t.originalText.slice(r.position.start.offset, r.position.end.offset).trimEnd())) : s.push(ca(Qv(e, t, n))), Pt(r) && !Gt(r, ["document", "documentHead"]) && s.push(av([r.type === "mappingValue" && !r.content ? "" : " ", e.parent.type === "mappingKey" && e.getParentNode(2).type === "mapping" && Pl(r) ? "" : Fu, n("trailingComment")])), zm(r) && s.push(Dt(r.type === "sequenceItem" ? 2 : 0, [ve, ut(ve, e.map(({ node: l }) => [hv(t.originalText, fa(l)) ? ve : "", n()], "endComments"))])), s.push(o), s;
}
function Qv(e, t, n) {
  let { node: r } = e;
  switch (r.type) {
    case "root": {
      let s = [];
      e.each(({ node: a, next: o, isFirst: l }) => {
        l || s.push(ve), s.push(n()), Gm(a, o) ? (s.push(ve, "..."), Pt(a) && s.push(" ", n("trailingComment"))) : o && !Pt(o.head) && s.push(ve, "---");
      }, "children");
      let i = Rl(r);
      return (!Gt(i, ["blockLiteral", "blockFolded"]) || i.chomping !== "keep") && s.push(ve), s;
    }
    case "document": {
      let s = [];
      return Xv(e, t) === "head" && ((r.head.children.length > 0 || r.head.endComments.length > 0) && s.push(n("head")), Pt(r.head) ? s.push(["---", " ", n(["head", "trailingComment"])]) : s.push("---")), Kv(r) && s.push(n("body")), ut(ve, s);
    }
    case "documentHead":
      return ut(ve, [...e.map(n, "children"), ...e.map(n, "endComments")]);
    case "documentBody": {
      let { children: s, endComments: i } = r, a = "";
      if (s.length > 0 && i.length > 0) {
        let o = Rl(r);
        Gt(o, ["blockFolded", "blockLiteral"]) ? o.chomping !== "keep" && (a = [ve, ve]) : a = ve;
      }
      return [ut(ve, e.map(n, "children")), a, ut(ve, e.map(n, "endComments"))];
    }
    case "directive":
      return ["%", ut(" ", [r.name, ...r.parameters])];
    case "comment":
      return ["#", r.value];
    case "alias":
      return ["*", r.value];
    case "tag":
      return t.originalText.slice(r.position.start.offset, r.position.end.offset);
    case "anchor":
      return ["&", r.value];
    case "plain":
      return As(r.type, t.originalText.slice(r.position.start.offset, r.position.end.offset), t);
    case "quoteDouble":
    case "quoteSingle": {
      let s = "'", i = '"', a = t.originalText.slice(r.position.start.offset + 1, r.position.end.offset - 1);
      if (r.type === "quoteSingle" && a.includes("\\") || r.type === "quoteDouble" && /\\[^"]/u.test(a)) {
        let l = r.type === "quoteDouble" ? i : s;
        return [l, As(r.type, a, t), l];
      }
      if (a.includes(i)) return [s, As(r.type, r.type === "quoteDouble" ? uo(!1, uo(!1, a, String.raw`\"`, i), "'", s.repeat(2)) : a, t), s];
      if (a.includes(s)) return [i, As(r.type, r.type === "quoteSingle" ? uo(!1, a, "''", s) : a, t), i];
      let o = t.singleQuote ? s : i;
      return [o, As(r.type, a, t), o];
    }
    case "blockFolded":
    case "blockLiteral":
      return Vv(e, t, n);
    case "mapping":
    case "sequence":
      return ut(ve, e.map(n, "children"));
    case "sequenceItem":
      return ["- ", Dt(2, r.content ? n("content") : "")];
    case "mappingKey":
    case "mappingValue":
      return r.content ? n("content") : "";
    case "mappingItem":
    case "flowMappingItem":
      return Hv(e, t, n);
    case "flowMapping":
      return nd(e, t, n);
    case "flowSequence":
      return nd(e, t, n);
    case "flowSequenceItem":
      return n("content");
    default:
      throw new mv(r, "YAML");
  }
}
function Kv(e) {
  return e.body.children.length > 0 || Lt(e.body);
}
function Gm(e, t) {
  return Pt(e) || t && (t.head.children.length > 0 || Lt(t.head));
}
function Xv(e, t) {
  let n = e.node;
  if (e.isFirst && /---(?:\s|$)/u.test(t.originalText.slice(fa(n), fa(n) + 4)) || n.head.children.length > 0 || Lt(n.head) || Pt(n.head)) return "head";
  let r = e.next;
  return Gm(n, r) ? !1 : r ? "root" : !1;
}
function As(e, t, n) {
  let r = Iv(e, t, n);
  return ut(ve, r.map((s) => Bm(ut(si, s))));
}
function Jm(e, t) {
  if (Gt(e)) switch (e.type) {
    case "comment":
      if (Cv(e.value)) return null;
      break;
    case "quoteDouble":
    case "quoteSingle":
      t.type = "quote";
      break;
  }
}
Jm.ignoredProperties = /* @__PURE__ */ new Set(["position"]);
var Zv = { preprocess: Gv, embed: pv, print: Jv, massageAstNode: Jm, insertPragma: Tv, getVisitorKeys: Ev }, ew = Zv, Qm = [{ name: "YAML", type: "data", extensions: [".yml", ".mir", ".reek", ".rviz", ".sublime-syntax", ".syntax", ".yaml", ".yaml-tmlanguage", ".yaml.sed", ".yml.mysql"], tmScope: "source.yaml", aceMode: "yaml", aliases: ["yml"], codemirrorMode: "yaml", codemirrorMimeType: "text/x-yaml", filenames: [".clang-format", ".clang-tidy", ".clangd", ".gemrc", "CITATION.cff", "glide.lock", "pixi.lock", ".prettierrc", ".stylelintrc", ".lintstagedrc"], parsers: ["yaml"], vscodeLanguageIds: ["yaml", "ansible", "dockercompose", "github-actions-workflow", "home-assistant"], linguistLanguageId: 407 }], ho = { bracketSpacing: { category: "Common", type: "boolean", default: !0, description: "Print spaces between brackets.", oppositeDescription: "Do not print spaces between brackets." }, singleQuote: { category: "Common", type: "boolean", default: !1, description: "Use single quotes instead of double quotes." }, proseWrap: { category: "Common", type: "choice", default: "preserve", description: "How to wrap prose.", choices: [{ value: "always", description: "Wrap prose if it exceeds the print width." }, { value: "never", description: "Do not wrap prose." }, { value: "preserve", description: "Wrap prose as-is." }] } }, tw = { bracketSpacing: ho.bracketSpacing, singleQuote: ho.singleQuote, proseWrap: ho.proseWrap }, Km = tw, _u = {};
mm(_u, { yaml: () => hD });
var rd = Su(Lm()), _t = Su(Y2());
_t.default.findPair;
_t.default.toJSON;
_t.default.parseMap;
_t.default.parseSeq;
_t.default.stringifyNumber;
_t.default.stringifyString;
_t.default.Type;
_t.default.YAMLError;
_t.default.YAMLReferenceError;
var nw = _t.default.YAMLSemanticError;
_t.default.YAMLSyntaxError;
_t.default.YAMLWarning;
function gt(e, t = null) {
  "children" in e && e.children.forEach((n) => gt(n, e)), "anchor" in e && e.anchor && gt(e.anchor, e), "tag" in e && e.tag && gt(e.tag, e), "leadingComments" in e && e.leadingComments.forEach((n) => gt(n, e)), "middleComments" in e && e.middleComments.forEach((n) => gt(n, e)), "indicatorComment" in e && e.indicatorComment && gt(e.indicatorComment, e), "trailingComment" in e && e.trailingComment && gt(e.trailingComment, e), "endComments" in e && e.endComments.forEach((n) => gt(n, e)), Object.defineProperty(e, "_parent", { value: t, enumerable: !1 });
}
function da(e) {
  return `${e.line}:${e.column}`;
}
function rw(e) {
  gt(e);
  let t = sw(e), n = e.children.slice();
  e.comments.sort((r, s) => r.position.start.offset - s.position.end.offset).filter((r) => !r._parent).forEach((r) => {
    for (; n.length > 1 && r.position.start.line > n[0].position.end.line; ) n.shift();
    iw(r, t, n[0]);
  });
}
function sw(e) {
  let t = Array.from(new Array(e.position.end.line), () => ({}));
  for (let n of e.comments) t[n.position.start.line - 1].comment = n;
  return Xm(t, e), t;
}
function Xm(e, t) {
  if (t.position.start.offset !== t.position.end.offset) {
    if ("leadingComments" in t) {
      let { start: n } = t.position, { leadingAttachableNode: r } = e[n.line - 1];
      (!r || n.column < r.position.start.column) && (e[n.line - 1].leadingAttachableNode = t);
    }
    if ("trailingComment" in t && t.position.end.column > 1 && t.type !== "document" && t.type !== "documentHead") {
      let { end: n } = t.position, { trailingAttachableNode: r } = e[n.line - 1];
      (!r || n.column >= r.position.end.column) && (e[n.line - 1].trailingAttachableNode = t);
    }
    if (t.type !== "root" && t.type !== "document" && t.type !== "documentHead" && t.type !== "documentBody") {
      let { start: n, end: r } = t.position, s = [r.line].concat(n.line === r.line ? [] : n.line);
      for (let i of s) {
        let a = e[i - 1].trailingNode;
        (!a || r.column >= a.position.end.column) && (e[i - 1].trailingNode = t);
      }
    }
    "children" in t && t.children.forEach((n) => {
      Xm(e, n);
    });
  }
}
function iw(e, t, n) {
  let r = e.position.start.line, { trailingAttachableNode: s } = t[r - 1];
  if (s) {
    if (s.trailingComment) throw new Error(`Unexpected multiple trailing comment at ${da(e.position.start)}`);
    gt(e, s), s.trailingComment = e;
    return;
  }
  for (let a = r; a >= n.position.start.line; a--) {
    let { trailingNode: o } = t[a - 1], l;
    if (o) l = o;
    else if (a !== r && t[a - 1].comment) l = t[a - 1].comment._parent;
    else continue;
    if ((l.type === "sequence" || l.type === "mapping") && (l = l.children[0]), l.type === "mappingItem") {
      let [u, f] = l.children;
      l = Zm(u) ? u : f;
    }
    for (; ; ) {
      if (aw(l, e)) {
        gt(e, l), l.endComments.push(e);
        return;
      }
      if (!l._parent) break;
      l = l._parent;
    }
    break;
  }
  for (let a = r + 1; a <= n.position.end.line; a++) {
    let { leadingAttachableNode: o } = t[a - 1];
    if (o) {
      gt(e, o), o.leadingComments.push(e);
      return;
    }
  }
  let i = n.children[1];
  gt(e, i), i.endComments.push(e);
}
function aw(e, t) {
  if (e.position.start.offset < t.position.start.offset && e.position.end.offset > t.position.end.offset) switch (e.type) {
    case "flowMapping":
    case "flowSequence":
      return e.children.length === 0 || t.position.start.line > e.children[e.children.length - 1].position.end.line;
  }
  if (t.position.end.offset < e.position.end.offset) return !1;
  switch (e.type) {
    case "sequenceItem":
      return t.position.start.column > e.position.start.column;
    case "mappingKey":
    case "mappingValue":
      return t.position.start.column > e._parent.position.start.column && (e.children.length === 0 || e.children.length === 1 && e.children[0].type !== "blockFolded" && e.children[0].type !== "blockLiteral") && (e.type === "mappingValue" || Zm(e));
    default:
      return !1;
  }
}
function Zm(e) {
  return e.position.start !== e.position.end && (e.children.length === 0 || e.position.start.offset !== e.children[0].position.start.offset);
}
function je(e, t) {
  return { type: e, position: t };
}
function ow(e, t, n) {
  return { ...je("root", e), children: t, comments: n };
}
function Pi(e) {
  switch (e.type) {
    case "DOCUMENT":
      for (let t = e.contents.length - 1; t >= 0; t--) e.contents[t].type === "BLANK_LINE" ? e.contents.splice(t, 1) : Pi(e.contents[t]);
      for (let t = e.directives.length - 1; t >= 0; t--) e.directives[t].type === "BLANK_LINE" && e.directives.splice(t, 1);
      break;
    case "FLOW_MAP":
    case "FLOW_SEQ":
    case "MAP":
    case "SEQ":
      for (let t = e.items.length - 1; t >= 0; t--) {
        let n = e.items[t];
        "char" in n || (n.type === "BLANK_LINE" ? e.items.splice(t, 1) : Pi(n));
      }
      break;
    case "MAP_KEY":
    case "MAP_VALUE":
    case "SEQ_ITEM":
      e.node && Pi(e.node);
      break;
    case "ALIAS":
    case "BLANK_LINE":
    case "BLOCK_FOLDED":
    case "BLOCK_LITERAL":
    case "COMMENT":
    case "DIRECTIVE":
    case "PLAIN":
    case "QUOTE_DOUBLE":
    case "QUOTE_SINGLE":
      break;
    default:
      throw new Error(`Unexpected node type ${JSON.stringify(e.type)}`);
  }
}
function lr(e, t) {
  return { start: e, end: t };
}
function sd(e) {
  return { start: e, end: e };
}
var Jr;
(function(e) {
  e.Tag = "!", e.Anchor = "&", e.Comment = "#";
})(Jr || (Jr = {}));
function lw(e, t) {
  return { ...je("anchor", e), value: t };
}
function Tu(e, t) {
  return { ...je("comment", e), value: t };
}
function uw(e, t, n) {
  return { anchor: t, tag: e, middleComments: n };
}
function cw(e, t) {
  return { ...je("tag", e), value: t };
}
function ep(e, t, n = () => !1) {
  let r = e.cstNode, s = [], i = null, a = null, o = null;
  for (let l of r.props) {
    let u = t.text[l.origStart];
    switch (u) {
      case Jr.Tag:
        i = i || l, a = cw(t.transformRange(l), e.tag);
        break;
      case Jr.Anchor:
        i = i || l, o = lw(t.transformRange(l), r.anchor);
        break;
      case Jr.Comment: {
        let f = Tu(t.transformRange(l), t.text.slice(l.origStart + 1, l.origEnd));
        t.comments.push(f), !n(f) && i && i.origEnd <= l.origStart && l.origEnd <= r.valueRange.origStart && s.push(f);
        break;
      }
      default:
        throw new Error(`Unexpected leading character ${JSON.stringify(u)}`);
    }
  }
  return uw(a, o, s);
}
function ds() {
  return { leadingComments: [] };
}
function Ra(e = null) {
  return { trailingComment: e };
}
function hr() {
  return { ...ds(), ...Ra() };
}
function fw(e, t, n) {
  return { ...je("alias", e), ...hr(), ...t, value: n };
}
function hw(e, t) {
  let n = e.cstNode;
  return fw(t.transformRange({ origStart: n.valueRange.origStart - 1, origEnd: n.valueRange.origEnd }), t.transformContent(e), n.rawValue);
}
function dw(e) {
  return { ...e, type: "blockFolded" };
}
function mw(e, t, n, r, s, i) {
  return { ...je("blockValue", e), ...ds(), ...t, chomping: n, indent: r, value: s, indicatorComment: i };
}
var Il;
(function(e) {
  e.CLIP = "clip", e.STRIP = "strip", e.KEEP = "keep";
})(Il || (Il = {}));
function tp(e, t) {
  let n = e.cstNode, r = 1, s = n.chomping === "CLIP" ? 0 : 1, i = n.header.origEnd - n.header.origStart - r - s !== 0, a = t.transformRange({ origStart: n.header.origStart, origEnd: n.valueRange.origEnd }), o = null, l = ep(e, t, (u) => {
    if (!(a.start.offset < u.position.start.offset && u.position.end.offset < a.end.offset)) return !1;
    if (o) throw new Error(`Unexpected multiple indicator comments at ${da(u.position.start)}`);
    return o = u, !0;
  });
  return mw(a, l, Il[n.chomping], i ? n.blockIndent : null, n.strValue, o);
}
function pw(e, t) {
  return dw(tp(e, t));
}
function gw(e) {
  return { ...e, type: "blockLiteral" };
}
function yw(e, t) {
  return gw(tp(e, t));
}
function bw(e, t) {
  return Tu(t.transformRange(e.range), e.comment);
}
function vw(e, t, n) {
  return { ...je("directive", e), ...hr(), name: t, parameters: n };
}
function Mu(e, t) {
  for (let n of e.props) {
    let r = t.text[n.origStart];
    switch (r) {
      case Jr.Comment:
        t.comments.push(Tu(t.transformRange(n), t.text.slice(n.origStart + 1, n.origEnd)));
        break;
      default:
        throw new Error(`Unexpected leading character ${JSON.stringify(r)}`);
    }
  }
}
function ww(e, t) {
  return Mu(e, t), vw(t.transformRange(e.range), e.name, e.parameters);
}
function Dw(e, t, n, r) {
  return { ...je("document", e), ...Ra(r), children: [t, n] };
}
function dr(e = []) {
  return { endComments: e };
}
function Sw(e, t, n) {
  return { ...je("documentBody", e), ...dr(n), children: t ? [t] : [] };
}
function Rn(e) {
  return e[e.length - 1];
}
function np(e, t) {
  let n = e.match(t);
  return n ? n.index : -1;
}
function Ew(e, t, n) {
  let r = e.cstNode, { comments: s, endComments: i, documentTrailingComment: a, documentHeadTrailingComment: o } = Aw(r, t, n), l = t.transformNode(e.contents), { position: u, documentEndPoint: f } = xw(r, l, t);
  return t.comments.push(...s, ...i), { documentBody: Sw(u, l, i), documentEndPoint: f, documentTrailingComment: a, documentHeadTrailingComment: o };
}
function Aw(e, t, n) {
  let r = [], s = [], i = [], a = [], o = !1;
  for (let l = e.contents.length - 1; l >= 0; l--) {
    let u = e.contents[l];
    if (u.type === "COMMENT") {
      let f = t.transformNode(u);
      n && n.line === f.position.start.line ? a.unshift(f) : o ? r.unshift(f) : f.position.start.offset >= e.valueRange.origEnd ? i.unshift(f) : r.unshift(f);
    } else o = !0;
  }
  if (i.length > 1) throw new Error(`Unexpected multiple document trailing comments at ${da(i[1].position.start)}`);
  if (a.length > 1) throw new Error(`Unexpected multiple documentHead trailing comments at ${da(a[1].position.start)}`);
  return { comments: r, endComments: s, documentTrailingComment: Rn(i) || null, documentHeadTrailingComment: Rn(a) || null };
}
function xw(e, t, n) {
  let r = np(n.text.slice(e.valueRange.origEnd), /^\.\.\./), s = r === -1 ? e.valueRange.origEnd : Math.max(0, e.valueRange.origEnd - 1);
  n.text[s - 1] === "\r" && s--;
  let i = n.transformRange({ origStart: t !== null ? t.position.start.offset : s, origEnd: s }), a = r === -1 ? i.end : n.transformOffset(e.valueRange.origEnd + 3);
  return { position: i, documentEndPoint: a };
}
function Nw(e, t, n, r) {
  return { ...je("documentHead", e), ...dr(n), ...Ra(r), children: t };
}
function Lw(e, t) {
  let n = e.cstNode, { directives: r, comments: s, endComments: i } = kw(n, t), { position: a, endMarkerPoint: o } = Cw(n, r, t);
  return t.comments.push(...s, ...i), { createDocumentHeadWithTrailingComment: (l) => (l && t.comments.push(l), Nw(a, r, i, l)), documentHeadEndMarkerPoint: o };
}
function kw(e, t) {
  let n = [], r = [], s = [], i = !1;
  for (let a = e.directives.length - 1; a >= 0; a--) {
    let o = t.transformNode(e.directives[a]);
    o.type === "comment" ? i ? r.unshift(o) : s.unshift(o) : (i = !0, n.unshift(o));
  }
  return { directives: n, comments: r, endComments: s };
}
function Cw(e, t, n) {
  let r = np(n.text.slice(0, e.valueRange.origStart), /---\s*$/);
  r > 0 && !/[\r\n]/.test(n.text[r - 1]) && (r = -1);
  let s = r === -1 ? { origStart: e.valueRange.origStart, origEnd: e.valueRange.origStart } : { origStart: r, origEnd: r + 3 };
  return t.length !== 0 && (s.origStart = t[0].position.start.offset), { position: n.transformRange(s), endMarkerPoint: r === -1 ? null : n.transformOffset(r) };
}
function Fw(e, t) {
  let { createDocumentHeadWithTrailingComment: n, documentHeadEndMarkerPoint: r } = Lw(e, t), { documentBody: s, documentEndPoint: i, documentTrailingComment: a, documentHeadTrailingComment: o } = Ew(e, t, r), l = n(o);
  return a && t.comments.push(a), Dw(lr(l.position.start, i), l, s, a);
}
function rp(e, t, n) {
  return { ...je("flowCollection", e), ...hr(), ...dr(), ...t, children: n };
}
function _w(e, t, n) {
  return { ...rp(e, t, n), type: "flowMapping" };
}
function sp(e, t, n) {
  return { ...je("flowMappingItem", e), ...ds(), children: [t, n] };
}
function Pa(e, t) {
  let n = [];
  for (let r of e) r && "type" in r && r.type === "COMMENT" ? t.comments.push(t.transformNode(r)) : n.push(r);
  return n;
}
function ip(e) {
  let [t, n] = ["?", ":"].map((r) => {
    let s = e.find((i) => "char" in i && i.char === r);
    return s ? { origStart: s.origOffset, origEnd: s.origOffset + 1 } : null;
  });
  return { additionalKeyRange: t, additionalValueRange: n };
}
function ap(e, t) {
  let n = t;
  return (r) => e.slice(n, n = r);
}
function op(e) {
  let t = [], n = ap(e, 1), r = !1;
  for (let s = 1; s < e.length - 1; s++) {
    let i = e[s];
    if ("char" in i && i.char === ",") {
      t.push(n(s)), n(s + 1), r = !1;
      continue;
    }
    r = !0;
  }
  return r && t.push(n(e.length - 1)), t;
}
function id(e, t) {
  return { ...je("mappingKey", e), ...Ra(), ...dr(), children: t ? [t] : [] };
}
function ad(e, t) {
  return { ...je("mappingValue", e), ...hr(), ...dr(), children: t ? [t] : [] };
}
function Ou(e, t, n, r, s) {
  let i = t.transformNode(e.key), a = t.transformNode(e.value), o = i || r ? id(t.transformRange({ origStart: r ? r.origStart : i.position.start.offset, origEnd: i ? i.position.end.offset : r.origStart + 1 }), i) : null, l = a || s ? ad(t.transformRange({ origStart: s ? s.origStart : a.position.start.offset, origEnd: a ? a.position.end.offset : s.origStart + 1 }), a) : null;
  return n(lr(o ? o.position.start : l.position.start, l ? l.position.end : o.position.end), o || id(sd(l.position.start), null), l || ad(sd(o.position.end), null));
}
function Tw(e, t) {
  let n = Pa(e.cstNode.items, t), r = op(n), s = e.items.map((o, l) => {
    let u = r[l], { additionalKeyRange: f, additionalValueRange: c } = ip(u);
    return Ou(o, t, sp, f, c);
  }), i = n[0], a = Rn(n);
  return _w(t.transformRange({ origStart: i.origOffset, origEnd: a.origOffset + 1 }), t.transformContent(e), s);
}
function Mw(e, t, n) {
  return { ...rp(e, t, n), type: "flowSequence" };
}
function Ow(e, t) {
  return { ...je("flowSequenceItem", e), children: [t] };
}
function Rw(e, t) {
  let n = Pa(e.cstNode.items, t), r = op(n), s = e.items.map((o, l) => {
    if (o.type !== "PAIR") {
      let u = t.transformNode(o);
      return Ow(lr(u.position.start, u.position.end), u);
    } else {
      let u = r[l], { additionalKeyRange: f, additionalValueRange: c } = ip(u);
      return Ou(o, t, sp, f, c);
    }
  }), i = n[0], a = Rn(n);
  return Mw(t.transformRange({ origStart: i.origOffset, origEnd: a.origOffset + 1 }), t.transformContent(e), s);
}
function Pw(e, t, n) {
  return { ...je("mapping", e), ...ds(), ...t, children: n };
}
function Iw(e, t, n) {
  return { ...je("mappingItem", e), ...ds(), children: [t, n] };
}
function $w(e, t) {
  let n = e.cstNode;
  n.items.filter((a) => a.type === "MAP_KEY" || a.type === "MAP_VALUE").forEach((a) => Mu(a, t));
  let r = Pa(n.items, t), s = Bw(r), i = e.items.map((a, o) => {
    let l = s[o], [u, f] = l[0].type === "MAP_VALUE" ? [null, l[0].range] : [l[0].range, l.length === 1 ? null : l[1].range];
    return Ou(a, t, Iw, u, f);
  });
  return Pw(lr(i[0].position.start, Rn(i).position.end), t.transformContent(e), i);
}
function Bw(e) {
  let t = [], n = ap(e, 0), r = !1;
  for (let s = 0; s < e.length; s++) {
    if (e[s].type === "MAP_VALUE") {
      t.push(n(s + 1)), r = !1;
      continue;
    }
    r && t.push(n(s)), r = !0;
  }
  return r && t.push(n(1 / 0)), t;
}
function Vw(e, t, n) {
  return { ...je("plain", e), ...hr(), ...t, value: n };
}
function jw(e, t, n) {
  for (let r = t; r >= 0; r--) if (n.test(e[r])) return r;
  return -1;
}
function Uw(e, t) {
  let n = e.cstNode;
  return Vw(t.transformRange({ origStart: n.valueRange.origStart, origEnd: jw(t.text, n.valueRange.origEnd - 1, /\S/) + 1 }), t.transformContent(e), n.strValue);
}
function qw(e) {
  return { ...e, type: "quoteDouble" };
}
function Ww(e, t, n) {
  return { ...je("quoteValue", e), ...t, ...hr(), value: n };
}
function lp(e, t) {
  let n = e.cstNode;
  return Ww(t.transformRange(n.valueRange), t.transformContent(e), n.strValue);
}
function Hw(e, t) {
  return qw(lp(e, t));
}
function Yw(e) {
  return { ...e, type: "quoteSingle" };
}
function zw(e, t) {
  return Yw(lp(e, t));
}
function Gw(e, t, n) {
  return { ...je("sequence", e), ...ds(), ...dr(), ...t, children: n };
}
function Jw(e, t) {
  return { ...je("sequenceItem", e), ...hr(), ...dr(), children: t ? [t] : [] };
}
function Qw(e, t) {
  let n = Pa(e.cstNode.items, t).map((r, s) => {
    Mu(r, t);
    let i = t.transformNode(e.items[s]);
    return Jw(lr(t.transformOffset(r.valueRange.origStart), i === null ? t.transformOffset(r.valueRange.origStart + 1) : i.position.end), i);
  });
  return Gw(lr(n[0].position.start, Rn(n).position.end), t.transformContent(e), n);
}
function Kw(e, t) {
  if (e === null || e.type === void 0 && e.value === null) return null;
  switch (e.type) {
    case "ALIAS":
      return hw(e, t);
    case "BLOCK_FOLDED":
      return pw(e, t);
    case "BLOCK_LITERAL":
      return yw(e, t);
    case "COMMENT":
      return bw(e, t);
    case "DIRECTIVE":
      return ww(e, t);
    case "DOCUMENT":
      return Fw(e, t);
    case "FLOW_MAP":
      return Tw(e, t);
    case "FLOW_SEQ":
      return Rw(e, t);
    case "MAP":
      return $w(e, t);
    case "PLAIN":
      return Uw(e, t);
    case "QUOTE_DOUBLE":
      return Hw(e, t);
    case "QUOTE_SINGLE":
      return zw(e, t);
    case "SEQ":
      return Qw(e, t);
    default:
      throw new Error(`Unexpected node type ${e.type}`);
  }
}
var mo, Or, Cs, Qr, $l, po, Xw = class {
  constructor(t, n) {
    lo(this, Qr), Qh(this, "text"), Qh(this, "comments", []), lo(this, Or), lo(this, Cs), this.text = n, pm(this, Or, t);
  }
  setOrigRanges() {
    if (!Ps(this, Or).setOrigRanges()) for (let t of Ps(this, Or)) t.setOrigRanges([], 0);
  }
  transformOffset(t) {
    return ua(this, Qr, $l).call(this, { origStart: t, origEnd: t }).start;
  }
  transformRange(t) {
    let { start: n, end: r } = ua(this, Qr, $l).call(this, t);
    return lr(n, r);
  }
  transformNode(t) {
    return Kw(t, this);
  }
  transformContent(t) {
    return ep(t, this);
  }
};
Or = /* @__PURE__ */ new WeakMap(), Cs = /* @__PURE__ */ new WeakMap(), Qr = /* @__PURE__ */ new WeakSet(), $l = function(e) {
  if (!mo) {
    let [i] = Ps(this, Or), a = Object.getPrototypeOf(Object.getPrototypeOf(i));
    mo = Object.getOwnPropertyDescriptor(a, "rangeAsLinePos").get;
  }
  Ps(this, Cs) ?? pm(this, Cs, { root: { context: { src: this.text } } });
  let { start: { line: t, col: n }, end: { line: r, col: s } } = mo.call({ range: { start: ua(this, Qr, po).call(this, e.origStart), end: ua(this, Qr, po).call(this, e.origEnd) }, context: Ps(this, Cs) });
  return { start: { offset: e.origStart, line: t, column: n }, end: { offset: e.origEnd, line: r, column: s } };
}, po = function(e) {
  return e < 0 ? 0 : e > this.text.length ? this.text.length : e;
};
var Zw = Xw;
function eD(e, t, n) {
  let r = new SyntaxError(e);
  return r.name = "YAMLSyntaxError", r.source = t, r.position = n, r;
}
function tD(e, t) {
  let n = e.source.range || e.source.valueRange;
  return eD(e.message, t.text, t.transformRange(n));
}
function up(e) {
  if ("children" in e) {
    if (e.children.length === 1) {
      let t = e.children[0];
      if (t.type === "plain" && t.tag === null && t.anchor === null && t.value === "") return e.children.splice(0, 1), e;
    }
    e.children.forEach(up);
  }
  return e;
}
function od(e, t, n, r) {
  let s = t(e);
  return (i) => {
    r(s, i) && n(e, s = i);
  };
}
function cp(e) {
  if (e === null || !("children" in e)) return;
  let t = e.children;
  if (t.forEach(cp), e.type === "document") {
    let [i, a] = e.children;
    i.position.start.offset === i.position.end.offset ? i.position.start = i.position.end = a.position.start : a.position.start.offset === a.position.end.offset && (a.position.start = a.position.end = i.position.end);
  }
  let n = od(e.position, nD, rD, aD), r = od(e.position, sD, iD, oD);
  "endComments" in e && e.endComments.length !== 0 && (n(e.endComments[0].position.start), r(Rn(e.endComments).position.end));
  let s = t.filter((i) => i !== null);
  if (s.length !== 0) {
    let i = s[0], a = Rn(s);
    n(i.position.start), r(a.position.end), "leadingComments" in i && i.leadingComments.length !== 0 && n(i.leadingComments[0].position.start), "tag" in i && i.tag && n(i.tag.position.start), "anchor" in i && i.anchor && n(i.anchor.position.start), "trailingComment" in a && a.trailingComment && r(a.trailingComment.position.end);
  }
}
function nD(e) {
  return e.start;
}
function rD(e, t) {
  e.start = t;
}
function sD(e) {
  return e.end;
}
function iD(e, t) {
  e.end = t;
}
function aD(e, t) {
  return t.offset < e.offset;
}
function oD(e, t) {
  return t.offset > e.offset;
}
function lD(e) {
  let t = rd.default.parseCST(e), n = new Zw(t, e);
  n.setOrigRanges();
  let r = t.map((i) => new rd.default.Document({ merge: !1, keepCstNodes: !0 }).parse(i));
  for (let i of r) for (let a of i.errors) if (!(a instanceof nw && a.message === 'Map keys must be unique; "<<" is repeated')) throw tD(a, n);
  r.forEach((i) => Pi(i.cstNode));
  let s = ow(n.transformRange({ origStart: 0, origEnd: e.length }), r.map((i) => n.transformNode(i)), n.comments);
  return rw(s), cp(s), up(s), s;
}
function uD(e, t) {
  let n = new SyntaxError(e + " (" + t.loc.start.line + ":" + t.loc.start.column + ")");
  return Object.assign(n, t);
}
var cD = uD;
function fD(e) {
  try {
    let t = lD(e);
    return delete t.comments, t;
  } catch (t) {
    throw t != null && t.position ? cD(t.message, { loc: t.position, cause: t }) : t;
  }
}
var hD = { astFormat: "yaml", parse: fD, hasPragma: Fv, hasIgnorePragma: _v, locStart: fa, locEnd: Av }, fp = { yaml: ew }, dD = Su(Lm()), hp = dD.default.parse, mD = km, pD = /* @__PURE__ */ Object.freeze({
  __proto__: null,
  __parsePrettierYamlConfig: hp,
  default: mD,
  languages: Qm,
  options: Km,
  parsers: _u,
  printers: fp
}), gD = Object.create, Ru = Object.defineProperty, yD = Object.getOwnPropertyDescriptor, bD = Object.getOwnPropertyNames, vD = Object.getPrototypeOf, wD = Object.prototype.hasOwnProperty, dp = (e) => {
  throw TypeError(e);
}, DD = (e, t) => () => (t || e((t = { exports: {} }).exports, t), t.exports), Pu = (e, t) => {
  for (var n in t) Ru(e, n, { get: t[n], enumerable: !0 });
}, SD = (e, t, n, r) => {
  if (t && typeof t == "object" || typeof t == "function") for (let s of bD(t)) !wD.call(e, s) && s !== n && Ru(e, s, { get: () => t[s], enumerable: !(r = yD(t, s)) || r.enumerable });
  return e;
}, ED = (e, t, n) => (n = e != null ? gD(vD(e)) : {}, SD(Ru(n, "default", { value: e, enumerable: !0 }), e)), AD = (e, t, n) => t.has(e) || dp("Cannot " + n), xD = (e, t, n) => t.has(e) ? dp("Cannot add the same private member more than once") : t instanceof WeakSet ? t.add(e) : t.set(e, n), xs = (e, t, n) => (AD(e, t, "access private method"), n), ND = DD((e) => {
  Object.defineProperty(e, "__esModule", { value: !0 });
  function t() {
    return new Proxy({}, { get: () => (i) => i });
  }
  var n = /\r\n|[\n\r\u2028\u2029]/;
  function r(i, a, o) {
    let l = Object.assign({ column: 0, line: -1 }, i.start), u = Object.assign({}, l, i.end), { linesAbove: f = 2, linesBelow: c = 3 } = o || {}, d = l.line, v = l.column, D = u.line, S = u.column, x = Math.max(d - (f + 1), 0), N = Math.min(a.length, D + c);
    d === -1 && (x = 0), D === -1 && (N = a.length);
    let k = D - d, y = {};
    if (k) for (let b = 0; b <= k; b++) {
      let h = b + d;
      if (!v) y[h] = !0;
      else if (b === 0) {
        let m = a[h - 1].length;
        y[h] = [v, m - v + 1];
      } else if (b === k) y[h] = [0, S];
      else {
        let m = a[h - b].length;
        y[h] = [0, m];
      }
    }
    else v === S ? v ? y[d] = [v, 0] : y[d] = !0 : y[d] = [v, S - v];
    return { start: x, end: N, markerLines: y };
  }
  function s(i, a, o = {}) {
    let l = t(), u = i.split(n), { start: f, end: c, markerLines: d } = r(a, u, o), v = a.start && typeof a.start.column == "number", D = String(c).length, S = i.split(n, c).slice(f, c).map((x, N) => {
      let k = f + 1 + N, y = ` ${` ${k}`.slice(-D)} |`, b = d[k], h = !d[k + 1];
      if (b) {
        let m = "";
        if (Array.isArray(b)) {
          let p = x.slice(0, Math.max(b[0] - 1, 0)).replace(/[^\t]/g, " "), E = b[1] || 1;
          m = [`
 `, l.gutter(y.replace(/\d/g, " ")), " ", p, l.marker("^").repeat(E)].join(""), h && o.message && (m += " " + l.message(o.message));
        }
        return [l.marker(">"), l.gutter(y), x.length > 0 ? ` ${x}` : "", m].join("");
      } else return ` ${l.gutter(y)}${x.length > 0 ? ` ${x}` : ""}`;
    }).join(`
`);
    return o.message && !v && (S = `${" ".repeat(D + 1)}${o.message}
${S}`), S;
  }
  e.codeFrameColumns = s;
}), LD = {};
Pu(LD, { __debug: () => V8, check: () => $8, doc: () => Qp, format: () => Ku, formatWithCursor: () => Xp, getSupportInfo: () => B8, util: () => Kp, version: () => h8 });
var kD = (e, t, n, r) => {
  if (!(e && t == null)) return t.replaceAll ? t.replaceAll(n, r) : n.global ? t.replace(n, r) : t.split(n).join(r);
}, Ia = kD, CD = class {
  diff(e, t, n = {}) {
    let r;
    typeof n == "function" ? (r = n, n = {}) : "callback" in n && (r = n.callback);
    let s = this.castInput(e, n), i = this.castInput(t, n), a = this.removeEmpty(this.tokenize(s, n)), o = this.removeEmpty(this.tokenize(i, n));
    return this.diffWithOptionsObj(a, o, n, r);
  }
  diffWithOptionsObj(e, t, n, r) {
    var s;
    let i = (N) => {
      if (N = this.postProcess(N, n), r) {
        setTimeout(function() {
          r(N);
        }, 0);
        return;
      } else return N;
    }, a = t.length, o = e.length, l = 1, u = a + o;
    n.maxEditLength != null && (u = Math.min(u, n.maxEditLength));
    let f = (s = n.timeout) !== null && s !== void 0 ? s : 1 / 0, c = Date.now() + f, d = [{ oldPos: -1, lastComponent: void 0 }], v = this.extractCommon(d[0], t, e, 0, n);
    if (d[0].oldPos + 1 >= o && v + 1 >= a) return i(this.buildValues(d[0].lastComponent, t, e));
    let D = -1 / 0, S = 1 / 0, x = () => {
      for (let N = Math.max(D, -l); N <= Math.min(S, l); N += 2) {
        let k, y = d[N - 1], b = d[N + 1];
        y && (d[N - 1] = void 0);
        let h = !1;
        if (b) {
          let p = b.oldPos - N;
          h = b && 0 <= p && p < a;
        }
        let m = y && y.oldPos + 1 < o;
        if (!h && !m) {
          d[N] = void 0;
          continue;
        }
        if (!m || h && y.oldPos < b.oldPos ? k = this.addToPath(b, !0, !1, 0, n) : k = this.addToPath(y, !1, !0, 1, n), v = this.extractCommon(k, t, e, N, n), k.oldPos + 1 >= o && v + 1 >= a) return i(this.buildValues(k.lastComponent, t, e)) || !0;
        d[N] = k, k.oldPos + 1 >= o && (S = Math.min(S, N - 1)), v + 1 >= a && (D = Math.max(D, N + 1));
      }
      l++;
    };
    if (r) (function N() {
      setTimeout(function() {
        if (l > u || Date.now() > c) return r(void 0);
        x() || N();
      }, 0);
    })();
    else for (; l <= u && Date.now() <= c; ) {
      let N = x();
      if (N) return N;
    }
  }
  addToPath(e, t, n, r, s) {
    let i = e.lastComponent;
    return i && !s.oneChangePerToken && i.added === t && i.removed === n ? { oldPos: e.oldPos + r, lastComponent: { count: i.count + 1, added: t, removed: n, previousComponent: i.previousComponent } } : { oldPos: e.oldPos + r, lastComponent: { count: 1, added: t, removed: n, previousComponent: i } };
  }
  extractCommon(e, t, n, r, s) {
    let i = t.length, a = n.length, o = e.oldPos, l = o - r, u = 0;
    for (; l + 1 < i && o + 1 < a && this.equals(n[o + 1], t[l + 1], s); ) l++, o++, u++, s.oneChangePerToken && (e.lastComponent = { count: 1, previousComponent: e.lastComponent, added: !1, removed: !1 });
    return u && !s.oneChangePerToken && (e.lastComponent = { count: u, previousComponent: e.lastComponent, added: !1, removed: !1 }), e.oldPos = o, l;
  }
  equals(e, t, n) {
    return n.comparator ? n.comparator(e, t) : e === t || !!n.ignoreCase && e.toLowerCase() === t.toLowerCase();
  }
  removeEmpty(e) {
    let t = [];
    for (let n = 0; n < e.length; n++) e[n] && t.push(e[n]);
    return t;
  }
  castInput(e, t) {
    return e;
  }
  tokenize(e, t) {
    return Array.from(e);
  }
  join(e) {
    return e.join("");
  }
  postProcess(e, t) {
    return e;
  }
  get useLongestToken() {
    return !1;
  }
  buildValues(e, t, n) {
    let r = [], s;
    for (; e; ) r.push(e), s = e.previousComponent, delete e.previousComponent, e = s;
    r.reverse();
    let i = r.length, a = 0, o = 0, l = 0;
    for (; a < i; a++) {
      let u = r[a];
      if (u.removed) u.value = this.join(n.slice(l, l + u.count)), l += u.count;
      else {
        if (!u.added && this.useLongestToken) {
          let f = t.slice(o, o + u.count);
          f = f.map(function(c, d) {
            let v = n[l + d];
            return v.length > c.length ? v : c;
          }), u.value = this.join(f);
        } else u.value = this.join(t.slice(o, o + u.count));
        o += u.count, u.added || (l += u.count);
      }
    }
    return r;
  }
}, FD = class extends CD {
  tokenize(e) {
    return e.slice();
  }
  join(e) {
    return e;
  }
  removeEmpty(e) {
    return e;
  }
}, _D = new FD();
function TD(e, t, n) {
  return _D.diff(e, t, n);
}
function MD(e) {
  let t = e.indexOf("\r");
  return t !== -1 ? e.charAt(t + 1) === `
` ? "crlf" : "cr" : "lf";
}
function Iu(e) {
  switch (e) {
    case "cr":
      return "\r";
    case "crlf":
      return `\r
`;
    default:
      return `
`;
  }
}
function mp(e, t) {
  let n;
  switch (t) {
    case `
`:
      n = /\n/gu;
      break;
    case "\r":
      n = /\r/gu;
      break;
    case `\r
`:
      n = /\r\n/gu;
      break;
    default:
      throw new Error(`Unexpected "eol" ${JSON.stringify(t)}.`);
  }
  let r = e.match(n);
  return r ? r.length : 0;
}
function OD(e) {
  return Ia(!1, e, /\r\n?/gu, `
`);
}
var mr = "string", mn = "array", $n = "cursor", gn = "indent", yn = "align", bn = "trim", ht = "group", Kt = "fill", vt = "if-break", vn = "indent-if-break", wn = "line-suffix", Dn = "line-suffix-boundary", Je = "line", Xt = "label", Ft = "break-parent", pp = /* @__PURE__ */ new Set([$n, gn, yn, bn, ht, Kt, vt, vn, wn, Dn, Je, Xt, Ft]), RD = (e, t, n) => {
  if (!(e && t == null)) return Array.isArray(t) || typeof t == "string" ? t[n < 0 ? t.length + n : n] : t.at(n);
}, He = RD;
function PD(e) {
  let t = e.length;
  for (; t > 0 && (e[t - 1] === "\r" || e[t - 1] === `
`); ) t--;
  return t < e.length ? e.slice(0, t) : e;
}
function ID(e) {
  if (typeof e == "string") return mr;
  if (Array.isArray(e)) return mn;
  if (!e) return;
  let { type: t } = e;
  if (pp.has(t)) return t;
}
var pr = ID, $D = (e) => new Intl.ListFormat("en-US", { type: "disjunction" }).format(e);
function BD(e) {
  let t = e === null ? "null" : typeof e;
  if (t !== "string" && t !== "object") return `Unexpected doc '${t}', 
Expected it to be 'string' or 'object'.`;
  if (pr(e)) throw new Error("doc is valid.");
  let n = Object.prototype.toString.call(e);
  if (n !== "[object Object]") return `Unexpected doc '${n}'.`;
  let r = $D([...pp].map((s) => `'${s}'`));
  return `Unexpected doc.type '${e.type}'.
Expected it to be ${r}.`;
}
var VD = class extends Error {
  name = "InvalidDocError";
  constructor(e) {
    super(BD(e)), this.doc = e;
  }
}, is = VD, ld = {};
function jD(e, t, n, r) {
  let s = [e];
  for (; s.length > 0; ) {
    let i = s.pop();
    if (i === ld) {
      n(s.pop());
      continue;
    }
    n && s.push(i, ld);
    let a = pr(i);
    if (!a) throw new is(i);
    if (t?.(i) !== !1) switch (a) {
      case mn:
      case Kt: {
        let o = a === mn ? i : i.parts;
        for (let l = o.length, u = l - 1; u >= 0; --u) s.push(o[u]);
        break;
      }
      case vt:
        s.push(i.flatContents, i.breakContents);
        break;
      case ht:
        if (r && i.expandedStates) for (let o = i.expandedStates.length, l = o - 1; l >= 0; --l) s.push(i.expandedStates[l]);
        else s.push(i.contents);
        break;
      case yn:
      case gn:
      case vn:
      case Xt:
      case wn:
        s.push(i.contents);
        break;
      case mr:
      case $n:
      case bn:
      case Dn:
      case Je:
      case Ft:
        break;
      default:
        throw new is(i);
    }
  }
}
var $u = jD;
function $a(e, t) {
  if (typeof e == "string") return t(e);
  let n = /* @__PURE__ */ new Map();
  return r(e);
  function r(i) {
    if (n.has(i)) return n.get(i);
    let a = s(i);
    return n.set(i, a), a;
  }
  function s(i) {
    switch (pr(i)) {
      case mn:
        return t(i.map(r));
      case Kt:
        return t({ ...i, parts: i.parts.map(r) });
      case vt:
        return t({ ...i, breakContents: r(i.breakContents), flatContents: r(i.flatContents) });
      case ht: {
        let { expandedStates: a, contents: o } = i;
        return a ? (a = a.map(r), o = a[0]) : o = r(o), t({ ...i, contents: o, expandedStates: a });
      }
      case yn:
      case gn:
      case vn:
      case Xt:
      case wn:
        return t({ ...i, contents: r(i.contents) });
      case mr:
      case $n:
      case bn:
      case Dn:
      case Je:
      case Ft:
        return t(i);
      default:
        throw new is(i);
    }
  }
}
function Bu(e, t, n) {
  let r = n, s = !1;
  function i(a) {
    if (s) return !1;
    let o = t(a);
    o !== void 0 && (s = !0, r = o);
  }
  return $u(e, i), r;
}
function UD(e) {
  if (e.type === ht && e.break || e.type === Je && e.hard || e.type === Ft) return !0;
}
function qD(e) {
  return Bu(e, UD, !1);
}
function ud(e) {
  if (e.length > 0) {
    let t = He(!1, e, -1);
    !t.expandedStates && !t.break && (t.break = "propagated");
  }
  return null;
}
function WD(e) {
  let t = /* @__PURE__ */ new Set(), n = [];
  function r(i) {
    if (i.type === Ft && ud(n), i.type === ht) {
      if (n.push(i), t.has(i)) return !1;
      t.add(i);
    }
  }
  function s(i) {
    i.type === ht && n.pop().break && ud(n);
  }
  $u(e, r, s, !0);
}
function HD(e) {
  return e.type === Je && !e.hard ? e.soft ? "" : " " : e.type === vt ? e.flatContents : e;
}
function YD(e) {
  return $a(e, HD);
}
function cd(e) {
  for (e = [...e]; e.length >= 2 && He(!1, e, -2).type === Je && He(!1, e, -1).type === Ft; ) e.length -= 2;
  if (e.length > 0) {
    let t = $s(He(!1, e, -1));
    e[e.length - 1] = t;
  }
  return e;
}
function $s(e) {
  switch (pr(e)) {
    case gn:
    case vn:
    case ht:
    case wn:
    case Xt: {
      let t = $s(e.contents);
      return { ...e, contents: t };
    }
    case vt:
      return { ...e, breakContents: $s(e.breakContents), flatContents: $s(e.flatContents) };
    case Kt:
      return { ...e, parts: cd(e.parts) };
    case mn:
      return cd(e);
    case mr:
      return PD(e);
    case yn:
    case $n:
    case bn:
    case Dn:
    case Je:
    case Ft:
      break;
    default:
      throw new is(e);
  }
  return e;
}
function gp(e) {
  return $s(GD(e));
}
function zD(e) {
  switch (pr(e)) {
    case Kt:
      if (e.parts.every((t) => t === "")) return "";
      break;
    case ht:
      if (!e.contents && !e.id && !e.break && !e.expandedStates) return "";
      if (e.contents.type === ht && e.contents.id === e.id && e.contents.break === e.break && e.contents.expandedStates === e.expandedStates) return e.contents;
      break;
    case yn:
    case gn:
    case vn:
    case wn:
      if (!e.contents) return "";
      break;
    case vt:
      if (!e.flatContents && !e.breakContents) return "";
      break;
    case mn: {
      let t = [];
      for (let n of e) {
        if (!n) continue;
        let [r, ...s] = Array.isArray(n) ? n : [n];
        typeof r == "string" && typeof He(!1, t, -1) == "string" ? t[t.length - 1] += r : t.push(r), t.push(...s);
      }
      return t.length === 0 ? "" : t.length === 1 ? t[0] : t;
    }
    case mr:
    case $n:
    case bn:
    case Dn:
    case Je:
    case Xt:
    case Ft:
      break;
    default:
      throw new is(e);
  }
  return e;
}
function GD(e) {
  return $a(e, (t) => zD(t));
}
function JD(e, t = wp) {
  return $a(e, (n) => typeof n == "string" ? Dp(t, n.split(`
`)) : n);
}
function QD(e) {
  if (e.type === Je) return !0;
}
function KD(e) {
  return Bu(e, QD, !1);
}
function Ii(e, t) {
  return e.type === Xt ? { ...e, contents: t(e.contents) } : t(e);
}
var XD = () => {
}, ZD = XD;
function ma(e) {
  return { type: gn, contents: e };
}
function as(e, t) {
  return { type: yn, contents: t, n: e };
}
function yp(e, t = {}) {
  return ZD(t.expandedStates), { type: ht, id: t.id, contents: e, break: !!t.shouldBreak, expandedStates: t.expandedStates };
}
function e9(e) {
  return as(Number.NEGATIVE_INFINITY, e);
}
function t9(e) {
  return as({ type: "root" }, e);
}
function n9(e) {
  return as(-1, e);
}
function r9(e, t) {
  return yp(e[0], { ...t, expandedStates: e });
}
function s9(e) {
  return { type: Kt, parts: e };
}
function i9(e, t = "", n = {}) {
  return { type: vt, breakContents: e, flatContents: t, groupId: n.groupId };
}
function a9(e, t) {
  return { type: vn, contents: e, groupId: t.groupId, negate: t.negate };
}
function Bl(e) {
  return { type: wn, contents: e };
}
var o9 = { type: Dn }, Ba = { type: Ft }, l9 = { type: bn }, Vu = { type: Je, hard: !0 }, bp = { type: Je, hard: !0, literal: !0 }, vp = { type: Je }, u9 = { type: Je, soft: !0 }, rr = [Vu, Ba], wp = [bp, Ba], Zn = { type: $n };
function Dp(e, t) {
  let n = [];
  for (let r = 0; r < t.length; r++) r !== 0 && n.push(e), n.push(t[r]);
  return n;
}
function Sp(e, t, n) {
  let r = e;
  if (t > 0) {
    for (let s = 0; s < Math.floor(t / n); ++s) r = ma(r);
    r = as(t % n, r), r = as(Number.NEGATIVE_INFINITY, r);
  }
  return r;
}
function c9(e, t) {
  return e ? { type: Xt, label: e, contents: t } : t;
}
function an(e) {
  var t;
  if (!e) return "";
  if (Array.isArray(e)) {
    let n = [];
    for (let r of e) if (Array.isArray(r)) n.push(...an(r));
    else {
      let s = an(r);
      s !== "" && n.push(s);
    }
    return n;
  }
  return e.type === vt ? { ...e, breakContents: an(e.breakContents), flatContents: an(e.flatContents) } : e.type === ht ? { ...e, contents: an(e.contents), expandedStates: (t = e.expandedStates) == null ? void 0 : t.map(an) } : e.type === Kt ? { type: "fill", parts: e.parts.map(an) } : e.contents ? { ...e, contents: an(e.contents) } : e;
}
function f9(e) {
  let t = /* @__PURE__ */ Object.create(null), n = /* @__PURE__ */ new Set();
  return r(an(e));
  function r(i, a, o) {
    var l, u;
    if (typeof i == "string") return JSON.stringify(i);
    if (Array.isArray(i)) {
      let f = i.map(r).filter(Boolean);
      return f.length === 1 ? f[0] : `[${f.join(", ")}]`;
    }
    if (i.type === Je) {
      let f = ((l = o?.[a + 1]) == null ? void 0 : l.type) === Ft;
      return i.literal ? f ? "literalline" : "literallineWithoutBreakParent" : i.hard ? f ? "hardline" : "hardlineWithoutBreakParent" : i.soft ? "softline" : "line";
    }
    if (i.type === Ft) return ((u = o?.[a - 1]) == null ? void 0 : u.type) === Je && o[a - 1].hard ? void 0 : "breakParent";
    if (i.type === bn) return "trim";
    if (i.type === gn) return "indent(" + r(i.contents) + ")";
    if (i.type === yn) return i.n === Number.NEGATIVE_INFINITY ? "dedentToRoot(" + r(i.contents) + ")" : i.n < 0 ? "dedent(" + r(i.contents) + ")" : i.n.type === "root" ? "markAsRoot(" + r(i.contents) + ")" : "align(" + JSON.stringify(i.n) + ", " + r(i.contents) + ")";
    if (i.type === vt) return "ifBreak(" + r(i.breakContents) + (i.flatContents ? ", " + r(i.flatContents) : "") + (i.groupId ? (i.flatContents ? "" : ', ""') + `, { groupId: ${s(i.groupId)} }` : "") + ")";
    if (i.type === vn) {
      let f = [];
      i.negate && f.push("negate: true"), i.groupId && f.push(`groupId: ${s(i.groupId)}`);
      let c = f.length > 0 ? `, { ${f.join(", ")} }` : "";
      return `indentIfBreak(${r(i.contents)}${c})`;
    }
    if (i.type === ht) {
      let f = [];
      i.break && i.break !== "propagated" && f.push("shouldBreak: true"), i.id && f.push(`id: ${s(i.id)}`);
      let c = f.length > 0 ? `, { ${f.join(", ")} }` : "";
      return i.expandedStates ? `conditionalGroup([${i.expandedStates.map((d) => r(d)).join(",")}]${c})` : `group(${r(i.contents)}${c})`;
    }
    if (i.type === Kt) return `fill([${i.parts.map((f) => r(f)).join(", ")}])`;
    if (i.type === wn) return "lineSuffix(" + r(i.contents) + ")";
    if (i.type === Dn) return "lineSuffixBoundary";
    if (i.type === Xt) return `label(${JSON.stringify(i.label)}, ${r(i.contents)})`;
    if (i.type === $n) return "cursor";
    throw new Error("Unknown doc type " + i.type);
  }
  function s(i) {
    if (typeof i != "symbol") return JSON.stringify(String(i));
    if (i in t) return t[i];
    let a = i.description || "symbol";
    for (let o = 0; ; o++) {
      let l = a + (o > 0 ? ` #${o}` : "");
      if (!n.has(l)) return n.add(l), t[i] = `Symbol.for(${JSON.stringify(l)})`;
    }
  }
}
var h9 = () => /[#*0-9]\uFE0F?\u20E3|[\xA9\xAE\u203C\u2049\u2122\u2139\u2194-\u2199\u21A9\u21AA\u231A\u231B\u2328\u23CF\u23ED-\u23EF\u23F1\u23F2\u23F8-\u23FA\u24C2\u25AA\u25AB\u25B6\u25C0\u25FB\u25FC\u25FE\u2600-\u2604\u260E\u2611\u2614\u2615\u2618\u2620\u2622\u2623\u2626\u262A\u262E\u262F\u2638-\u263A\u2640\u2642\u2648-\u2653\u265F\u2660\u2663\u2665\u2666\u2668\u267B\u267E\u267F\u2692\u2694-\u2697\u2699\u269B\u269C\u26A0\u26A7\u26AA\u26B0\u26B1\u26BD\u26BE\u26C4\u26C8\u26CF\u26D1\u26E9\u26F0-\u26F5\u26F7\u26F8\u26FA\u2702\u2708\u2709\u270F\u2712\u2714\u2716\u271D\u2721\u2733\u2734\u2744\u2747\u2757\u2763\u27A1\u2934\u2935\u2B05-\u2B07\u2B1B\u2B1C\u2B55\u3030\u303D\u3297\u3299]\uFE0F?|[\u261D\u270C\u270D](?:\uD83C[\uDFFB-\uDFFF]|\uFE0F)?|[\u270A\u270B](?:\uD83C[\uDFFB-\uDFFF])?|[\u23E9-\u23EC\u23F0\u23F3\u25FD\u2693\u26A1\u26AB\u26C5\u26CE\u26D4\u26EA\u26FD\u2705\u2728\u274C\u274E\u2753-\u2755\u2795-\u2797\u27B0\u27BF\u2B50]|\u26D3\uFE0F?(?:\u200D\uD83D\uDCA5)?|\u26F9(?:\uD83C[\uDFFB-\uDFFF]|\uFE0F)?(?:\u200D[\u2640\u2642]\uFE0F?)?|\u2764\uFE0F?(?:\u200D(?:\uD83D\uDD25|\uD83E\uDE79))?|\uD83C(?:[\uDC04\uDD70\uDD71\uDD7E\uDD7F\uDE02\uDE37\uDF21\uDF24-\uDF2C\uDF36\uDF7D\uDF96\uDF97\uDF99-\uDF9B\uDF9E\uDF9F\uDFCD\uDFCE\uDFD4-\uDFDF\uDFF5\uDFF7]\uFE0F?|[\uDF85\uDFC2\uDFC7](?:\uD83C[\uDFFB-\uDFFF])?|[\uDFC4\uDFCA](?:\uD83C[\uDFFB-\uDFFF])?(?:\u200D[\u2640\u2642]\uFE0F?)?|[\uDFCB\uDFCC](?:\uD83C[\uDFFB-\uDFFF]|\uFE0F)?(?:\u200D[\u2640\u2642]\uFE0F?)?|[\uDCCF\uDD8E\uDD91-\uDD9A\uDE01\uDE1A\uDE2F\uDE32-\uDE36\uDE38-\uDE3A\uDE50\uDE51\uDF00-\uDF20\uDF2D-\uDF35\uDF37-\uDF43\uDF45-\uDF4A\uDF4C-\uDF7C\uDF7E-\uDF84\uDF86-\uDF93\uDFA0-\uDFC1\uDFC5\uDFC6\uDFC8\uDFC9\uDFCF-\uDFD3\uDFE0-\uDFF0\uDFF8-\uDFFF]|\uDDE6\uD83C[\uDDE8-\uDDEC\uDDEE\uDDF1\uDDF2\uDDF4\uDDF6-\uDDFA\uDDFC\uDDFD\uDDFF]|\uDDE7\uD83C[\uDDE6\uDDE7\uDDE9-\uDDEF\uDDF1-\uDDF4\uDDF6-\uDDF9\uDDFB\uDDFC\uDDFE\uDDFF]|\uDDE8\uD83C[\uDDE6\uDDE8\uDDE9\uDDEB-\uDDEE\uDDF0-\uDDF7\uDDFA-\uDDFF]|\uDDE9\uD83C[\uDDEA\uDDEC\uDDEF\uDDF0\uDDF2\uDDF4\uDDFF]|\uDDEA\uD83C[\uDDE6\uDDE8\uDDEA\uDDEC\uDDED\uDDF7-\uDDFA]|\uDDEB\uD83C[\uDDEE-\uDDF0\uDDF2\uDDF4\uDDF7]|\uDDEC\uD83C[\uDDE6\uDDE7\uDDE9-\uDDEE\uDDF1-\uDDF3\uDDF5-\uDDFA\uDDFC\uDDFE]|\uDDED\uD83C[\uDDF0\uDDF2\uDDF3\uDDF7\uDDF9\uDDFA]|\uDDEE\uD83C[\uDDE8-\uDDEA\uDDF1-\uDDF4\uDDF6-\uDDF9]|\uDDEF\uD83C[\uDDEA\uDDF2\uDDF4\uDDF5]|\uDDF0\uD83C[\uDDEA\uDDEC-\uDDEE\uDDF2\uDDF3\uDDF5\uDDF7\uDDFC\uDDFE\uDDFF]|\uDDF1\uD83C[\uDDE6-\uDDE8\uDDEE\uDDF0\uDDF7-\uDDFB\uDDFE]|\uDDF2\uD83C[\uDDE6\uDDE8-\uDDED\uDDF0-\uDDFF]|\uDDF3\uD83C[\uDDE6\uDDE8\uDDEA-\uDDEC\uDDEE\uDDF1\uDDF4\uDDF5\uDDF7\uDDFA\uDDFF]|\uDDF4\uD83C\uDDF2|\uDDF5\uD83C[\uDDE6\uDDEA-\uDDED\uDDF0-\uDDF3\uDDF7-\uDDF9\uDDFC\uDDFE]|\uDDF6\uD83C\uDDE6|\uDDF7\uD83C[\uDDEA\uDDF4\uDDF8\uDDFA\uDDFC]|\uDDF8\uD83C[\uDDE6-\uDDEA\uDDEC-\uDDF4\uDDF7-\uDDF9\uDDFB\uDDFD-\uDDFF]|\uDDF9\uD83C[\uDDE6\uDDE8\uDDE9\uDDEB-\uDDED\uDDEF-\uDDF4\uDDF7\uDDF9\uDDFB\uDDFC\uDDFF]|\uDDFA\uD83C[\uDDE6\uDDEC\uDDF2\uDDF3\uDDF8\uDDFE\uDDFF]|\uDDFB\uD83C[\uDDE6\uDDE8\uDDEA\uDDEC\uDDEE\uDDF3\uDDFA]|\uDDFC\uD83C[\uDDEB\uDDF8]|\uDDFD\uD83C\uDDF0|\uDDFE\uD83C[\uDDEA\uDDF9]|\uDDFF\uD83C[\uDDE6\uDDF2\uDDFC]|\uDF44(?:\u200D\uD83D\uDFEB)?|\uDF4B(?:\u200D\uD83D\uDFE9)?|\uDFC3(?:\uD83C[\uDFFB-\uDFFF])?(?:\u200D(?:[\u2640\u2642]\uFE0F?(?:\u200D\u27A1\uFE0F?)?|\u27A1\uFE0F?))?|\uDFF3\uFE0F?(?:\u200D(?:\u26A7\uFE0F?|\uD83C\uDF08))?|\uDFF4(?:\u200D\u2620\uFE0F?|\uDB40\uDC67\uDB40\uDC62\uDB40(?:\uDC65\uDB40\uDC6E\uDB40\uDC67|\uDC73\uDB40\uDC63\uDB40\uDC74|\uDC77\uDB40\uDC6C\uDB40\uDC73)\uDB40\uDC7F)?)|\uD83D(?:[\uDC3F\uDCFD\uDD49\uDD4A\uDD6F\uDD70\uDD73\uDD76-\uDD79\uDD87\uDD8A-\uDD8D\uDDA5\uDDA8\uDDB1\uDDB2\uDDBC\uDDC2-\uDDC4\uDDD1-\uDDD3\uDDDC-\uDDDE\uDDE1\uDDE3\uDDE8\uDDEF\uDDF3\uDDFA\uDECB\uDECD-\uDECF\uDEE0-\uDEE5\uDEE9\uDEF0\uDEF3]\uFE0F?|[\uDC42\uDC43\uDC46-\uDC50\uDC66\uDC67\uDC6B-\uDC6D\uDC72\uDC74-\uDC76\uDC78\uDC7C\uDC83\uDC85\uDC8F\uDC91\uDCAA\uDD7A\uDD95\uDD96\uDE4C\uDE4F\uDEC0\uDECC](?:\uD83C[\uDFFB-\uDFFF])?|[\uDC6E\uDC70\uDC71\uDC73\uDC77\uDC81\uDC82\uDC86\uDC87\uDE45-\uDE47\uDE4B\uDE4D\uDE4E\uDEA3\uDEB4\uDEB5](?:\uD83C[\uDFFB-\uDFFF])?(?:\u200D[\u2640\u2642]\uFE0F?)?|[\uDD74\uDD90](?:\uD83C[\uDFFB-\uDFFF]|\uFE0F)?|[\uDC00-\uDC07\uDC09-\uDC14\uDC16-\uDC25\uDC27-\uDC3A\uDC3C-\uDC3E\uDC40\uDC44\uDC45\uDC51-\uDC65\uDC6A\uDC79-\uDC7B\uDC7D-\uDC80\uDC84\uDC88-\uDC8E\uDC90\uDC92-\uDCA9\uDCAB-\uDCFC\uDCFF-\uDD3D\uDD4B-\uDD4E\uDD50-\uDD67\uDDA4\uDDFB-\uDE2D\uDE2F-\uDE34\uDE37-\uDE41\uDE43\uDE44\uDE48-\uDE4A\uDE80-\uDEA2\uDEA4-\uDEB3\uDEB7-\uDEBF\uDEC1-\uDEC5\uDED0-\uDED2\uDED5-\uDED7\uDEDC-\uDEDF\uDEEB\uDEEC\uDEF4-\uDEFC\uDFE0-\uDFEB\uDFF0]|\uDC08(?:\u200D\u2B1B)?|\uDC15(?:\u200D\uD83E\uDDBA)?|\uDC26(?:\u200D(?:\u2B1B|\uD83D\uDD25))?|\uDC3B(?:\u200D\u2744\uFE0F?)?|\uDC41\uFE0F?(?:\u200D\uD83D\uDDE8\uFE0F?)?|\uDC68(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D\uD83D(?:\uDC8B\u200D\uD83D)?\uDC68|\uD83C[\uDF3E\uDF73\uDF7C\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D(?:[\uDC68\uDC69]\u200D\uD83D(?:\uDC66(?:\u200D\uD83D\uDC66)?|\uDC67(?:\u200D\uD83D[\uDC66\uDC67])?)|[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uDC66(?:\u200D\uD83D\uDC66)?|\uDC67(?:\u200D\uD83D[\uDC66\uDC67])?)|\uD83E(?:[\uDDAF\uDDBC\uDDBD](?:\u200D\u27A1\uFE0F?)?|[\uDDB0-\uDDB3]))|\uD83C(?:\uDFFB(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D\uD83D(?:\uDC8B\u200D\uD83D)?\uDC68\uD83C[\uDFFB-\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uD83E(?:[\uDDAF\uDDBC\uDDBD](?:\u200D\u27A1\uFE0F?)?|[\uDDB0-\uDDB3]|\uDD1D\u200D\uD83D\uDC68\uD83C[\uDFFC-\uDFFF])))?|\uDFFC(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D\uD83D(?:\uDC8B\u200D\uD83D)?\uDC68\uD83C[\uDFFB-\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uD83E(?:[\uDDAF\uDDBC\uDDBD](?:\u200D\u27A1\uFE0F?)?|[\uDDB0-\uDDB3]|\uDD1D\u200D\uD83D\uDC68\uD83C[\uDFFB\uDFFD-\uDFFF])))?|\uDFFD(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D\uD83D(?:\uDC8B\u200D\uD83D)?\uDC68\uD83C[\uDFFB-\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uD83E(?:[\uDDAF\uDDBC\uDDBD](?:\u200D\u27A1\uFE0F?)?|[\uDDB0-\uDDB3]|\uDD1D\u200D\uD83D\uDC68\uD83C[\uDFFB\uDFFC\uDFFE\uDFFF])))?|\uDFFE(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D\uD83D(?:\uDC8B\u200D\uD83D)?\uDC68\uD83C[\uDFFB-\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uD83E(?:[\uDDAF\uDDBC\uDDBD](?:\u200D\u27A1\uFE0F?)?|[\uDDB0-\uDDB3]|\uDD1D\u200D\uD83D\uDC68\uD83C[\uDFFB-\uDFFD\uDFFF])))?|\uDFFF(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D\uD83D(?:\uDC8B\u200D\uD83D)?\uDC68\uD83C[\uDFFB-\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uD83E(?:[\uDDAF\uDDBC\uDDBD](?:\u200D\u27A1\uFE0F?)?|[\uDDB0-\uDDB3]|\uDD1D\u200D\uD83D\uDC68\uD83C[\uDFFB-\uDFFE])))?))?|\uDC69(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D\uD83D(?:\uDC8B\u200D\uD83D)?[\uDC68\uDC69]|\uD83C[\uDF3E\uDF73\uDF7C\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D(?:[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uDC66(?:\u200D\uD83D\uDC66)?|\uDC67(?:\u200D\uD83D[\uDC66\uDC67])?|\uDC69\u200D\uD83D(?:\uDC66(?:\u200D\uD83D\uDC66)?|\uDC67(?:\u200D\uD83D[\uDC66\uDC67])?))|\uD83E(?:[\uDDAF\uDDBC\uDDBD](?:\u200D\u27A1\uFE0F?)?|[\uDDB0-\uDDB3]))|\uD83C(?:\uDFFB(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D\uD83D(?:[\uDC68\uDC69]|\uDC8B\u200D\uD83D[\uDC68\uDC69])\uD83C[\uDFFB-\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uD83E(?:[\uDDAF\uDDBC\uDDBD](?:\u200D\u27A1\uFE0F?)?|[\uDDB0-\uDDB3]|\uDD1D\u200D\uD83D[\uDC68\uDC69]\uD83C[\uDFFC-\uDFFF])))?|\uDFFC(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D\uD83D(?:[\uDC68\uDC69]|\uDC8B\u200D\uD83D[\uDC68\uDC69])\uD83C[\uDFFB-\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uD83E(?:[\uDDAF\uDDBC\uDDBD](?:\u200D\u27A1\uFE0F?)?|[\uDDB0-\uDDB3]|\uDD1D\u200D\uD83D[\uDC68\uDC69]\uD83C[\uDFFB\uDFFD-\uDFFF])))?|\uDFFD(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D\uD83D(?:[\uDC68\uDC69]|\uDC8B\u200D\uD83D[\uDC68\uDC69])\uD83C[\uDFFB-\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uD83E(?:[\uDDAF\uDDBC\uDDBD](?:\u200D\u27A1\uFE0F?)?|[\uDDB0-\uDDB3]|\uDD1D\u200D\uD83D[\uDC68\uDC69]\uD83C[\uDFFB\uDFFC\uDFFE\uDFFF])))?|\uDFFE(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D\uD83D(?:[\uDC68\uDC69]|\uDC8B\u200D\uD83D[\uDC68\uDC69])\uD83C[\uDFFB-\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uD83E(?:[\uDDAF\uDDBC\uDDBD](?:\u200D\u27A1\uFE0F?)?|[\uDDB0-\uDDB3]|\uDD1D\u200D\uD83D[\uDC68\uDC69]\uD83C[\uDFFB-\uDFFD\uDFFF])))?|\uDFFF(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D\uD83D(?:[\uDC68\uDC69]|\uDC8B\u200D\uD83D[\uDC68\uDC69])\uD83C[\uDFFB-\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uD83E(?:[\uDDAF\uDDBC\uDDBD](?:\u200D\u27A1\uFE0F?)?|[\uDDB0-\uDDB3]|\uDD1D\u200D\uD83D[\uDC68\uDC69]\uD83C[\uDFFB-\uDFFE])))?))?|\uDC6F(?:\u200D[\u2640\u2642]\uFE0F?)?|\uDD75(?:\uD83C[\uDFFB-\uDFFF]|\uFE0F)?(?:\u200D[\u2640\u2642]\uFE0F?)?|\uDE2E(?:\u200D\uD83D\uDCA8)?|\uDE35(?:\u200D\uD83D\uDCAB)?|\uDE36(?:\u200D\uD83C\uDF2B\uFE0F?)?|\uDE42(?:\u200D[\u2194\u2195]\uFE0F?)?|\uDEB6(?:\uD83C[\uDFFB-\uDFFF])?(?:\u200D(?:[\u2640\u2642]\uFE0F?(?:\u200D\u27A1\uFE0F?)?|\u27A1\uFE0F?))?)|\uD83E(?:[\uDD0C\uDD0F\uDD18-\uDD1F\uDD30-\uDD34\uDD36\uDD77\uDDB5\uDDB6\uDDBB\uDDD2\uDDD3\uDDD5\uDEC3-\uDEC5\uDEF0\uDEF2-\uDEF8](?:\uD83C[\uDFFB-\uDFFF])?|[\uDD26\uDD35\uDD37-\uDD39\uDD3D\uDD3E\uDDB8\uDDB9\uDDCD\uDDCF\uDDD4\uDDD6-\uDDDD](?:\uD83C[\uDFFB-\uDFFF])?(?:\u200D[\u2640\u2642]\uFE0F?)?|[\uDDDE\uDDDF](?:\u200D[\u2640\u2642]\uFE0F?)?|[\uDD0D\uDD0E\uDD10-\uDD17\uDD20-\uDD25\uDD27-\uDD2F\uDD3A\uDD3F-\uDD45\uDD47-\uDD76\uDD78-\uDDB4\uDDB7\uDDBA\uDDBC-\uDDCC\uDDD0\uDDE0-\uDDFF\uDE70-\uDE7C\uDE80-\uDE89\uDE8F-\uDEC2\uDEC6\uDECE-\uDEDC\uDEDF-\uDEE9]|\uDD3C(?:\u200D[\u2640\u2642]\uFE0F?|\uD83C[\uDFFB-\uDFFF])?|\uDDCE(?:\uD83C[\uDFFB-\uDFFF])?(?:\u200D(?:[\u2640\u2642]\uFE0F?(?:\u200D\u27A1\uFE0F?)?|\u27A1\uFE0F?))?|\uDDD1(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\uD83C[\uDF3E\uDF73\uDF7C\uDF84\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uD83E(?:[\uDDAF\uDDBC\uDDBD](?:\u200D\u27A1\uFE0F?)?|[\uDDB0-\uDDB3]|\uDD1D\u200D\uD83E\uDDD1|\uDDD1\u200D\uD83E\uDDD2(?:\u200D\uD83E\uDDD2)?|\uDDD2(?:\u200D\uD83E\uDDD2)?))|\uD83C(?:\uDFFB(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D(?:\uD83D\uDC8B\u200D)?\uD83E\uDDD1\uD83C[\uDFFC-\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF84\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uD83E(?:[\uDDAF\uDDBC\uDDBD](?:\u200D\u27A1\uFE0F?)?|[\uDDB0-\uDDB3]|\uDD1D\u200D\uD83E\uDDD1\uD83C[\uDFFB-\uDFFF])))?|\uDFFC(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D(?:\uD83D\uDC8B\u200D)?\uD83E\uDDD1\uD83C[\uDFFB\uDFFD-\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF84\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uD83E(?:[\uDDAF\uDDBC\uDDBD](?:\u200D\u27A1\uFE0F?)?|[\uDDB0-\uDDB3]|\uDD1D\u200D\uD83E\uDDD1\uD83C[\uDFFB-\uDFFF])))?|\uDFFD(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D(?:\uD83D\uDC8B\u200D)?\uD83E\uDDD1\uD83C[\uDFFB\uDFFC\uDFFE\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF84\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uD83E(?:[\uDDAF\uDDBC\uDDBD](?:\u200D\u27A1\uFE0F?)?|[\uDDB0-\uDDB3]|\uDD1D\u200D\uD83E\uDDD1\uD83C[\uDFFB-\uDFFF])))?|\uDFFE(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D(?:\uD83D\uDC8B\u200D)?\uD83E\uDDD1\uD83C[\uDFFB-\uDFFD\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF84\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uD83E(?:[\uDDAF\uDDBC\uDDBD](?:\u200D\u27A1\uFE0F?)?|[\uDDB0-\uDDB3]|\uDD1D\u200D\uD83E\uDDD1\uD83C[\uDFFB-\uDFFF])))?|\uDFFF(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D(?:\uD83D\uDC8B\u200D)?\uD83E\uDDD1\uD83C[\uDFFB-\uDFFE]|\uD83C[\uDF3E\uDF73\uDF7C\uDF84\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uD83E(?:[\uDDAF\uDDBC\uDDBD](?:\u200D\u27A1\uFE0F?)?|[\uDDB0-\uDDB3]|\uDD1D\u200D\uD83E\uDDD1\uD83C[\uDFFB-\uDFFF])))?))?|\uDEF1(?:\uD83C(?:\uDFFB(?:\u200D\uD83E\uDEF2\uD83C[\uDFFC-\uDFFF])?|\uDFFC(?:\u200D\uD83E\uDEF2\uD83C[\uDFFB\uDFFD-\uDFFF])?|\uDFFD(?:\u200D\uD83E\uDEF2\uD83C[\uDFFB\uDFFC\uDFFE\uDFFF])?|\uDFFE(?:\u200D\uD83E\uDEF2\uD83C[\uDFFB-\uDFFD\uDFFF])?|\uDFFF(?:\u200D\uD83E\uDEF2\uD83C[\uDFFB-\uDFFE])?))?)/g;
function d9(e) {
  return e === 12288 || e >= 65281 && e <= 65376 || e >= 65504 && e <= 65510;
}
function m9(e) {
  return e >= 4352 && e <= 4447 || e === 8986 || e === 8987 || e === 9001 || e === 9002 || e >= 9193 && e <= 9196 || e === 9200 || e === 9203 || e === 9725 || e === 9726 || e === 9748 || e === 9749 || e >= 9776 && e <= 9783 || e >= 9800 && e <= 9811 || e === 9855 || e >= 9866 && e <= 9871 || e === 9875 || e === 9889 || e === 9898 || e === 9899 || e === 9917 || e === 9918 || e === 9924 || e === 9925 || e === 9934 || e === 9940 || e === 9962 || e === 9970 || e === 9971 || e === 9973 || e === 9978 || e === 9981 || e === 9989 || e === 9994 || e === 9995 || e === 10024 || e === 10060 || e === 10062 || e >= 10067 && e <= 10069 || e === 10071 || e >= 10133 && e <= 10135 || e === 10160 || e === 10175 || e === 11035 || e === 11036 || e === 11088 || e === 11093 || e >= 11904 && e <= 11929 || e >= 11931 && e <= 12019 || e >= 12032 && e <= 12245 || e >= 12272 && e <= 12287 || e >= 12289 && e <= 12350 || e >= 12353 && e <= 12438 || e >= 12441 && e <= 12543 || e >= 12549 && e <= 12591 || e >= 12593 && e <= 12686 || e >= 12688 && e <= 12773 || e >= 12783 && e <= 12830 || e >= 12832 && e <= 12871 || e >= 12880 && e <= 42124 || e >= 42128 && e <= 42182 || e >= 43360 && e <= 43388 || e >= 44032 && e <= 55203 || e >= 63744 && e <= 64255 || e >= 65040 && e <= 65049 || e >= 65072 && e <= 65106 || e >= 65108 && e <= 65126 || e >= 65128 && e <= 65131 || e >= 94176 && e <= 94180 || e === 94192 || e === 94193 || e >= 94208 && e <= 100343 || e >= 100352 && e <= 101589 || e >= 101631 && e <= 101640 || e >= 110576 && e <= 110579 || e >= 110581 && e <= 110587 || e === 110589 || e === 110590 || e >= 110592 && e <= 110882 || e === 110898 || e >= 110928 && e <= 110930 || e === 110933 || e >= 110948 && e <= 110951 || e >= 110960 && e <= 111355 || e >= 119552 && e <= 119638 || e >= 119648 && e <= 119670 || e === 126980 || e === 127183 || e === 127374 || e >= 127377 && e <= 127386 || e >= 127488 && e <= 127490 || e >= 127504 && e <= 127547 || e >= 127552 && e <= 127560 || e === 127568 || e === 127569 || e >= 127584 && e <= 127589 || e >= 127744 && e <= 127776 || e >= 127789 && e <= 127797 || e >= 127799 && e <= 127868 || e >= 127870 && e <= 127891 || e >= 127904 && e <= 127946 || e >= 127951 && e <= 127955 || e >= 127968 && e <= 127984 || e === 127988 || e >= 127992 && e <= 128062 || e === 128064 || e >= 128066 && e <= 128252 || e >= 128255 && e <= 128317 || e >= 128331 && e <= 128334 || e >= 128336 && e <= 128359 || e === 128378 || e === 128405 || e === 128406 || e === 128420 || e >= 128507 && e <= 128591 || e >= 128640 && e <= 128709 || e === 128716 || e >= 128720 && e <= 128722 || e >= 128725 && e <= 128727 || e >= 128732 && e <= 128735 || e === 128747 || e === 128748 || e >= 128756 && e <= 128764 || e >= 128992 && e <= 129003 || e === 129008 || e >= 129292 && e <= 129338 || e >= 129340 && e <= 129349 || e >= 129351 && e <= 129535 || e >= 129648 && e <= 129660 || e >= 129664 && e <= 129673 || e >= 129679 && e <= 129734 || e >= 129742 && e <= 129756 || e >= 129759 && e <= 129769 || e >= 129776 && e <= 129784 || e >= 131072 && e <= 196605 || e >= 196608 && e <= 262141;
}
var p9 = (e) => !(d9(e) || m9(e)), g9 = /[^\x20-\x7F]/u;
function y9(e) {
  if (!e) return 0;
  if (!g9.test(e)) return e.length;
  e = e.replace(h9(), "  ");
  let t = 0;
  for (let n of e) {
    let r = n.codePointAt(0);
    r <= 31 || r >= 127 && r <= 159 || r >= 768 && r <= 879 || (t += p9(r) ? 1 : 2);
  }
  return t;
}
var ju = y9, lt = Symbol("MODE_BREAK"), jt = Symbol("MODE_FLAT"), Rr = Symbol("cursor"), Vl = Symbol("DOC_FILL_PRINTED_LENGTH");
function Ep() {
  return { value: "", length: 0, queue: [] };
}
function b9(e, t) {
  return jl(e, { type: "indent" }, t);
}
function v9(e, t, n) {
  return t === Number.NEGATIVE_INFINITY ? e.root || Ep() : t < 0 ? jl(e, { type: "dedent" }, n) : t ? t.type === "root" ? { ...e, root: e } : jl(e, { type: typeof t == "string" ? "stringAlign" : "numberAlign", n: t }, n) : e;
}
function jl(e, t, n) {
  let r = t.type === "dedent" ? e.queue.slice(0, -1) : [...e.queue, t], s = "", i = 0, a = 0, o = 0;
  for (let D of r) switch (D.type) {
    case "indent":
      f(), n.useTabs ? l(1) : u(n.tabWidth);
      break;
    case "stringAlign":
      f(), s += D.n, i += D.n.length;
      break;
    case "numberAlign":
      a += 1, o += D.n;
      break;
    default:
      throw new Error(`Unexpected type '${D.type}'`);
  }
  return d(), { ...e, value: s, length: i, queue: r };
  function l(D) {
    s += "	".repeat(D), i += n.tabWidth * D;
  }
  function u(D) {
    s += " ".repeat(D), i += D;
  }
  function f() {
    n.useTabs ? c() : d();
  }
  function c() {
    a > 0 && l(a), v();
  }
  function d() {
    o > 0 && u(o), v();
  }
  function v() {
    a = 0, o = 0;
  }
}
function Ul(e) {
  let t = 0, n = 0, r = e.length;
  e: for (; r--; ) {
    let s = e[r];
    if (s === Rr) {
      n++;
      continue;
    }
    for (let i = s.length - 1; i >= 0; i--) {
      let a = s[i];
      if (a === " " || a === "	") t++;
      else {
        e[r] = s.slice(0, i + 1);
        break e;
      }
    }
  }
  if (t > 0 || n > 0) for (e.length = r + 1; n-- > 0; ) e.push(Rr);
  return t;
}
function yi(e, t, n, r, s, i) {
  if (n === Number.POSITIVE_INFINITY) return !0;
  let a = t.length, o = [e], l = [];
  for (; n >= 0; ) {
    if (o.length === 0) {
      if (a === 0) return !0;
      o.push(t[--a]);
      continue;
    }
    let { mode: u, doc: f } = o.pop(), c = pr(f);
    switch (c) {
      case mr:
        l.push(f), n -= ju(f);
        break;
      case mn:
      case Kt: {
        let d = c === mn ? f : f.parts, v = f[Vl] ?? 0;
        for (let D = d.length - 1; D >= v; D--) o.push({ mode: u, doc: d[D] });
        break;
      }
      case gn:
      case yn:
      case vn:
      case Xt:
        o.push({ mode: u, doc: f.contents });
        break;
      case bn:
        n += Ul(l);
        break;
      case ht: {
        if (i && f.break) return !1;
        let d = f.break ? lt : u, v = f.expandedStates && d === lt ? He(!1, f.expandedStates, -1) : f.contents;
        o.push({ mode: d, doc: v });
        break;
      }
      case vt: {
        let d = (f.groupId ? s[f.groupId] || jt : u) === lt ? f.breakContents : f.flatContents;
        d && o.push({ mode: u, doc: d });
        break;
      }
      case Je:
        if (u === lt || f.hard) return !0;
        f.soft || (l.push(" "), n--);
        break;
      case wn:
        r = !0;
        break;
      case Dn:
        if (r) return !1;
        break;
    }
  }
  return !1;
}
function Va(e, t) {
  let n = {}, r = t.printWidth, s = Iu(t.endOfLine), i = 0, a = [{ ind: Ep(), mode: lt, doc: e }], o = [], l = !1, u = [], f = 0;
  for (WD(e); a.length > 0; ) {
    let { ind: d, mode: v, doc: D } = a.pop();
    switch (pr(D)) {
      case mr: {
        let S = s !== `
` ? Ia(!1, D, `
`, s) : D;
        o.push(S), a.length > 0 && (i += ju(S));
        break;
      }
      case mn:
        for (let S = D.length - 1; S >= 0; S--) a.push({ ind: d, mode: v, doc: D[S] });
        break;
      case $n:
        if (f >= 2) throw new Error("There are too many 'cursor' in doc.");
        o.push(Rr), f++;
        break;
      case gn:
        a.push({ ind: b9(d, t), mode: v, doc: D.contents });
        break;
      case yn:
        a.push({ ind: v9(d, D.n, t), mode: v, doc: D.contents });
        break;
      case bn:
        i -= Ul(o);
        break;
      case ht:
        switch (v) {
          case jt:
            if (!l) {
              a.push({ ind: d, mode: D.break ? lt : jt, doc: D.contents });
              break;
            }
          case lt: {
            l = !1;
            let S = { ind: d, mode: jt, doc: D.contents }, x = r - i, N = u.length > 0;
            if (!D.break && yi(S, a, x, N, n)) a.push(S);
            else if (D.expandedStates) {
              let k = He(!1, D.expandedStates, -1);
              if (D.break) {
                a.push({ ind: d, mode: lt, doc: k });
                break;
              } else for (let y = 1; y < D.expandedStates.length + 1; y++) if (y >= D.expandedStates.length) {
                a.push({ ind: d, mode: lt, doc: k });
                break;
              } else {
                let b = D.expandedStates[y], h = { ind: d, mode: jt, doc: b };
                if (yi(h, a, x, N, n)) {
                  a.push(h);
                  break;
                }
              }
            } else a.push({ ind: d, mode: lt, doc: D.contents });
            break;
          }
        }
        D.id && (n[D.id] = He(!1, a, -1).mode);
        break;
      case Kt: {
        let S = r - i, x = D[Vl] ?? 0, { parts: N } = D, k = N.length - x;
        if (k === 0) break;
        let y = N[x + 0], b = N[x + 1], h = { ind: d, mode: jt, doc: y }, m = { ind: d, mode: lt, doc: y }, p = yi(h, [], S, u.length > 0, n, !0);
        if (k === 1) {
          p ? a.push(h) : a.push(m);
          break;
        }
        let E = { ind: d, mode: jt, doc: b }, w = { ind: d, mode: lt, doc: b };
        if (k === 2) {
          p ? a.push(E, h) : a.push(w, m);
          break;
        }
        let L = N[x + 2], C = { ind: d, mode: v, doc: { ...D, [Vl]: x + 2 } };
        yi({ ind: d, mode: jt, doc: [y, b, L] }, [], S, u.length > 0, n, !0) ? a.push(C, E, h) : p ? a.push(C, w, h) : a.push(C, w, m);
        break;
      }
      case vt:
      case vn: {
        let S = D.groupId ? n[D.groupId] : v;
        if (S === lt) {
          let x = D.type === vt ? D.breakContents : D.negate ? D.contents : ma(D.contents);
          x && a.push({ ind: d, mode: v, doc: x });
        }
        if (S === jt) {
          let x = D.type === vt ? D.flatContents : D.negate ? ma(D.contents) : D.contents;
          x && a.push({ ind: d, mode: v, doc: x });
        }
        break;
      }
      case wn:
        u.push({ ind: d, mode: v, doc: D.contents });
        break;
      case Dn:
        u.length > 0 && a.push({ ind: d, mode: v, doc: Vu });
        break;
      case Je:
        switch (v) {
          case jt:
            if (D.hard) l = !0;
            else {
              D.soft || (o.push(" "), i += 1);
              break;
            }
          case lt:
            if (u.length > 0) {
              a.push({ ind: d, mode: v, doc: D }, ...u.reverse()), u.length = 0;
              break;
            }
            D.literal ? d.root ? (o.push(s, d.root.value), i = d.root.length) : (o.push(s), i = 0) : (i -= Ul(o), o.push(s + d.value), i = d.length);
            break;
        }
        break;
      case Xt:
        a.push({ ind: d, mode: v, doc: D.contents });
        break;
      case Ft:
        break;
      default:
        throw new is(D);
    }
    a.length === 0 && u.length > 0 && (a.push(...u.reverse()), u.length = 0);
  }
  let c = o.indexOf(Rr);
  if (c !== -1) {
    let d = o.indexOf(Rr, c + 1);
    if (d === -1) return { formatted: o.filter((x) => x !== Rr).join("") };
    let v = o.slice(0, c).join(""), D = o.slice(c + 1, d).join(""), S = o.slice(d + 1).join("");
    return { formatted: v + D + S, cursorNodeStart: v.length, cursorNodeText: D };
  }
  return { formatted: o.join("") };
}
function w9(e, t, n = 0) {
  let r = 0;
  for (let s = n; s < e.length; ++s) e[s] === "	" ? r = r + t - r % t : r++;
  return r;
}
var Uu = w9, Wn, ql, $i, D9 = class {
  constructor(e) {
    xD(this, Wn), this.stack = [e];
  }
  get key() {
    let { stack: e, siblings: t } = this;
    return He(!1, e, t === null ? -2 : -4) ?? null;
  }
  get index() {
    return this.siblings === null ? null : He(!1, this.stack, -2);
  }
  get node() {
    return He(!1, this.stack, -1);
  }
  get parent() {
    return this.getNode(1);
  }
  get grandparent() {
    return this.getNode(2);
  }
  get isInArray() {
    return this.siblings !== null;
  }
  get siblings() {
    let { stack: e } = this, t = He(!1, e, -3);
    return Array.isArray(t) ? t : null;
  }
  get next() {
    let { siblings: e } = this;
    return e === null ? null : e[this.index + 1];
  }
  get previous() {
    let { siblings: e } = this;
    return e === null ? null : e[this.index - 1];
  }
  get isFirst() {
    return this.index === 0;
  }
  get isLast() {
    let { siblings: e, index: t } = this;
    return e !== null && t === e.length - 1;
  }
  get isRoot() {
    return this.stack.length === 1;
  }
  get root() {
    return this.stack[0];
  }
  get ancestors() {
    return [...xs(this, Wn, $i).call(this)];
  }
  getName() {
    let { stack: e } = this, { length: t } = e;
    return t > 1 ? He(!1, e, -2) : null;
  }
  getValue() {
    return He(!1, this.stack, -1);
  }
  getNode(e = 0) {
    let t = xs(this, Wn, ql).call(this, e);
    return t === -1 ? null : this.stack[t];
  }
  getParentNode(e = 0) {
    return this.getNode(e + 1);
  }
  call(e, ...t) {
    let { stack: n } = this, { length: r } = n, s = He(!1, n, -1);
    for (let i of t) s = s[i], n.push(i, s);
    try {
      return e(this);
    } finally {
      n.length = r;
    }
  }
  callParent(e, t = 0) {
    let n = xs(this, Wn, ql).call(this, t + 1), r = this.stack.splice(n + 1);
    try {
      return e(this);
    } finally {
      this.stack.push(...r);
    }
  }
  each(e, ...t) {
    let { stack: n } = this, { length: r } = n, s = He(!1, n, -1);
    for (let i of t) s = s[i], n.push(i, s);
    try {
      for (let i = 0; i < s.length; ++i) n.push(i, s[i]), e(this, i, s), n.length -= 2;
    } finally {
      n.length = r;
    }
  }
  map(e, ...t) {
    let n = [];
    return this.each((r, s, i) => {
      n[s] = e(r, s, i);
    }, ...t), n;
  }
  match(...e) {
    let t = this.stack.length - 1, n = null, r = this.stack[t--];
    for (let s of e) {
      if (r === void 0) return !1;
      let i = null;
      if (typeof n == "number" && (i = n, n = this.stack[t--], r = this.stack[t--]), s && !s(r, n, i)) return !1;
      n = this.stack[t--], r = this.stack[t--];
    }
    return !0;
  }
  findAncestor(e) {
    for (let t of xs(this, Wn, $i).call(this)) if (e(t)) return t;
  }
  hasAncestor(e) {
    for (let t of xs(this, Wn, $i).call(this)) if (e(t)) return !0;
    return !1;
  }
};
Wn = /* @__PURE__ */ new WeakSet(), ql = function(e) {
  let { stack: t } = this;
  for (let n = t.length - 1; n >= 0; n -= 2) if (!Array.isArray(t[n]) && --e < 0) return n;
  return -1;
}, $i = function* () {
  let { stack: e } = this;
  for (let t = e.length - 3; t >= 0; t -= 2) {
    let n = e[t];
    Array.isArray(n) || (yield n);
  }
};
var S9 = D9, Ap = new Proxy(() => {
}, { get: () => Ap }), Wl = Ap;
function E9(e) {
  return e !== null && typeof e == "object";
}
var A9 = E9;
function* ja(e, t) {
  let { getVisitorKeys: n, filter: r = () => !0 } = t, s = (i) => A9(i) && r(i);
  for (let i of n(e)) {
    let a = e[i];
    if (Array.isArray(a)) for (let o of a) s(o) && (yield o);
    else s(a) && (yield a);
  }
}
function* x9(e, t) {
  let n = [e];
  for (let r = 0; r < n.length; r++) {
    let s = n[r];
    for (let i of ja(s, t)) yield i, n.push(i);
  }
}
function N9(e, t) {
  return ja(e, t).next().done;
}
function ai(e) {
  return (t, n, r) => {
    let s = !!(r != null && r.backwards);
    if (n === !1) return !1;
    let { length: i } = t, a = n;
    for (; a >= 0 && a < i; ) {
      let o = t.charAt(a);
      if (e instanceof RegExp) {
        if (!e.test(o)) return a;
      } else if (!e.includes(o)) return a;
      s ? a-- : a++;
    }
    return a === -1 || a === i ? a : !1;
  };
}
var L9 = ai(/\s/u), Pn = ai(" 	"), xp = ai(",; 	"), Np = ai(/[^\n\r]/u);
function k9(e, t, n) {
  let r = !!(n != null && n.backwards);
  if (t === !1) return !1;
  let s = e.charAt(t);
  if (r) {
    if (e.charAt(t - 1) === "\r" && s === `
`) return t - 2;
    if (s === `
` || s === "\r" || s === "\u2028" || s === "\u2029") return t - 1;
  } else {
    if (s === "\r" && e.charAt(t + 1) === `
`) return t + 2;
    if (s === `
` || s === "\r" || s === "\u2028" || s === "\u2029") return t + 1;
  }
  return t;
}
var ur = k9;
function C9(e, t, n = {}) {
  let r = Pn(e, n.backwards ? t - 1 : t, n), s = ur(e, r, n);
  return r !== s;
}
var On = C9;
function F9(e) {
  return Array.isArray(e) && e.length > 0;
}
var _9 = F9, Lp = /* @__PURE__ */ new Set(["tokens", "comments", "parent", "enclosingNode", "precedingNode", "followingNode"]), T9 = (e) => Object.keys(e).filter((t) => !Lp.has(t));
function M9(e) {
  return e ? (t) => e(t, Lp) : T9;
}
var Ua = M9;
function O9(e) {
  let t = e.type || e.kind || "(unknown type)", n = String(e.name || e.id && (typeof e.id == "object" ? e.id.name : e.id) || e.key && (typeof e.key == "object" ? e.key.name : e.key) || e.value && (typeof e.value == "object" ? "" : String(e.value)) || e.operator || "");
  return n.length > 20 && (n = n.slice(0, 19) + "…"), t + (n ? " " + n : "");
}
function qu(e, t) {
  (e.comments ?? (e.comments = [])).push(t), t.printed = !1, t.nodeDescription = O9(e);
}
function Bs(e, t) {
  t.leading = !0, t.trailing = !1, qu(e, t);
}
function Hn(e, t, n) {
  t.leading = !1, t.trailing = !1, n && (t.marker = n), qu(e, t);
}
function Vs(e, t) {
  t.leading = !1, t.trailing = !0, qu(e, t);
}
var go = /* @__PURE__ */ new WeakMap();
function Wu(e, t) {
  if (go.has(e)) return go.get(e);
  let { printer: { getCommentChildNodes: n, canAttachComment: r, getVisitorKeys: s }, locStart: i, locEnd: a } = t;
  if (!r) return [];
  let o = (n?.(e, t) ?? [...ja(e, { getVisitorKeys: Ua(s) })]).flatMap((l) => r(l) ? [l] : Wu(l, t));
  return o.sort((l, u) => i(l) - i(u) || a(l) - a(u)), go.set(e, o), o;
}
function kp(e, t, n, r) {
  let { locStart: s, locEnd: i } = n, a = s(t), o = i(t), l = Wu(e, n), u, f, c = 0, d = l.length;
  for (; c < d; ) {
    let v = c + d >> 1, D = l[v], S = s(D), x = i(D);
    if (S <= a && o <= x) return kp(D, t, n, D);
    if (x <= a) {
      u = D, c = v + 1;
      continue;
    }
    if (o <= S) {
      f = D, d = v;
      continue;
    }
    throw new Error("Comment location overlaps with node location");
  }
  if (r?.type === "TemplateLiteral") {
    let { quasis: v } = r, D = bo(v, t, n);
    u && bo(v, u, n) !== D && (u = null), f && bo(v, f, n) !== D && (f = null);
  }
  return { enclosingNode: r, precedingNode: u, followingNode: f };
}
var yo = () => !1;
function R9(e, t) {
  let { comments: n } = e;
  if (delete e.comments, !_9(n) || !t.printer.canAttachComment) return;
  let r = [], { printer: { experimentalFeatures: { avoidAstMutation: s = !1 } = {}, handleComments: i = {} }, originalText: a } = t, { ownLine: o = yo, endOfLine: l = yo, remaining: u = yo } = i, f = n.map((c, d) => ({ ...kp(e, c, t), comment: c, text: a, options: t, ast: e, isLastComment: n.length - 1 === d }));
  for (let [c, d] of f.entries()) {
    let { comment: v, precedingNode: D, enclosingNode: S, followingNode: x, text: N, options: k, ast: y, isLastComment: b } = d, h;
    if (s ? h = [d] : (v.enclosingNode = S, v.precedingNode = D, v.followingNode = x, h = [v, N, k, y, b]), P9(N, k, f, c)) v.placement = "ownLine", o(...h) || (x ? Bs(x, v) : D ? Vs(D, v) : Hn(S || y, v));
    else if (I9(N, k, f, c)) v.placement = "endOfLine", l(...h) || (D ? Vs(D, v) : x ? Bs(x, v) : Hn(S || y, v));
    else if (v.placement = "remaining", !u(...h)) if (D && x) {
      let m = r.length;
      m > 0 && r[m - 1].followingNode !== x && fd(r, k), r.push(d);
    } else D ? Vs(D, v) : x ? Bs(x, v) : Hn(S || y, v);
  }
  if (fd(r, t), !s) for (let c of n) delete c.precedingNode, delete c.enclosingNode, delete c.followingNode;
}
var Cp = (e) => !/[\S\n\u2028\u2029]/u.test(e);
function P9(e, t, n, r) {
  let { comment: s, precedingNode: i } = n[r], { locStart: a, locEnd: o } = t, l = a(s);
  if (i) for (let u = r - 1; u >= 0; u--) {
    let { comment: f, precedingNode: c } = n[u];
    if (c !== i || !Cp(e.slice(o(f), l))) break;
    l = a(f);
  }
  return On(e, l, { backwards: !0 });
}
function I9(e, t, n, r) {
  let { comment: s, followingNode: i } = n[r], { locStart: a, locEnd: o } = t, l = o(s);
  if (i) for (let u = r + 1; u < n.length; u++) {
    let { comment: f, followingNode: c } = n[u];
    if (c !== i || !Cp(e.slice(l, a(f)))) break;
    l = o(f);
  }
  return On(e, l);
}
function fd(e, t) {
  var n, r;
  let s = e.length;
  if (s === 0) return;
  let { precedingNode: i, followingNode: a } = e[0], o = t.locStart(a), l;
  for (l = s; l > 0; --l) {
    let { comment: u, precedingNode: f, followingNode: c } = e[l - 1];
    Wl.strictEqual(f, i), Wl.strictEqual(c, a);
    let d = t.originalText.slice(t.locEnd(u), o);
    if (((r = (n = t.printer).isGap) == null ? void 0 : r.call(n, d, t)) ?? /^[\s(]*$/u.test(d)) o = t.locStart(u);
    else break;
  }
  for (let [u, { comment: f }] of e.entries()) u < l ? Vs(i, f) : Bs(a, f);
  for (let u of [i, a]) u.comments && u.comments.length > 1 && u.comments.sort((f, c) => t.locStart(f) - t.locStart(c));
  e.length = 0;
}
function bo(e, t, n) {
  let r = n.locStart(t) - 1;
  for (let s = 1; s < e.length; ++s) if (r < n.locStart(e[s])) return s - 1;
  return 0;
}
function $9(e, t) {
  let n = t - 1;
  n = Pn(e, n, { backwards: !0 }), n = ur(e, n, { backwards: !0 }), n = Pn(e, n, { backwards: !0 });
  let r = ur(e, n, { backwards: !0 });
  return n !== r;
}
var Hu = $9;
function Fp(e, t) {
  let n = e.node;
  return n.printed = !0, t.printer.printComment(e, t);
}
function B9(e, t) {
  var n;
  let r = e.node, s = [Fp(e, t)], { printer: i, originalText: a, locStart: o, locEnd: l } = t;
  if ((n = i.isBlockComment) != null && n.call(i, r)) {
    let f = On(a, l(r)) ? On(a, o(r), { backwards: !0 }) ? rr : vp : " ";
    s.push(f);
  } else s.push(rr);
  let u = ur(a, Pn(a, l(r)));
  return u !== !1 && On(a, u) && s.push(rr), s;
}
function V9(e, t, n) {
  var r;
  let s = e.node, i = Fp(e, t), { printer: a, originalText: o, locStart: l } = t, u = (r = a.isBlockComment) == null ? void 0 : r.call(a, s);
  if (n != null && n.hasLineSuffix && !(n != null && n.isBlock) || On(o, l(s), { backwards: !0 })) {
    let f = Hu(o, l(s));
    return { doc: Bl([rr, f ? rr : "", i]), isBlock: u, hasLineSuffix: !0 };
  }
  return !u || n != null && n.hasLineSuffix ? { doc: [Bl([" ", i]), Ba], isBlock: u, hasLineSuffix: !0 } : { doc: [" ", i], isBlock: u, hasLineSuffix: !1 };
}
function j9(e, t) {
  let n = e.node;
  if (!n) return {};
  let r = t[Symbol.for("printedComments")];
  if ((n.comments || []).filter((o) => !r.has(o)).length === 0) return { leading: "", trailing: "" };
  let s = [], i = [], a;
  return e.each(() => {
    let o = e.node;
    if (r != null && r.has(o)) return;
    let { leading: l, trailing: u } = o;
    l ? s.push(B9(e, t)) : u && (a = V9(e, t, a), i.push(a.doc));
  }, "comments"), { leading: s, trailing: i };
}
function U9(e, t, n) {
  let { leading: r, trailing: s } = j9(e, n);
  return !r && !s ? t : Ii(t, (i) => [r, i, s]);
}
function q9(e) {
  let { [Symbol.for("comments")]: t, [Symbol.for("printedComments")]: n } = e;
  for (let r of t) {
    if (!r.printed && !n.has(r)) throw new Error('Comment "' + r.value.trim() + '" was not printed. Please report this error!');
    delete r.printed;
  }
}
var _p = class extends Error {
  name = "ConfigError";
}, hd = class extends Error {
  name = "UndefinedParserError";
}, W9 = { checkIgnorePragma: { category: "Special", type: "boolean", default: !1, description: "Check whether the file's first docblock comment contains '@noprettier' or '@noformat' to determine if it should be formatted.", cliCategory: "Other" }, cursorOffset: { category: "Special", type: "int", default: -1, range: { start: -1, end: 1 / 0, step: 1 }, description: "Print (to stderr) where a cursor at the given position would move to after formatting.", cliCategory: "Editor" }, endOfLine: { category: "Global", type: "choice", default: "lf", description: "Which end of line characters to apply.", choices: [{ value: "lf", description: "Line Feed only (\\n), common on Linux and macOS as well as inside git repos" }, { value: "crlf", description: "Carriage Return + Line Feed characters (\\r\\n), common on Windows" }, { value: "cr", description: "Carriage Return character only (\\r), used very rarely" }, { value: "auto", description: `Maintain existing
(mixed values within one file are normalised by looking at what's used after the first line)` }] }, filepath: { category: "Special", type: "path", description: "Specify the input filepath. This will be used to do parser inference.", cliName: "stdin-filepath", cliCategory: "Other", cliDescription: "Path to the file to pretend that stdin comes from." }, insertPragma: { category: "Special", type: "boolean", default: !1, description: "Insert @format pragma into file's first docblock comment.", cliCategory: "Other" }, parser: { category: "Global", type: "choice", default: void 0, description: "Which parser to use.", exception: (e) => typeof e == "string" || typeof e == "function", choices: [{ value: "flow", description: "Flow" }, { value: "babel", description: "JavaScript" }, { value: "babel-flow", description: "Flow" }, { value: "babel-ts", description: "TypeScript" }, { value: "typescript", description: "TypeScript" }, { value: "acorn", description: "JavaScript" }, { value: "espree", description: "JavaScript" }, { value: "meriyah", description: "JavaScript" }, { value: "css", description: "CSS" }, { value: "less", description: "Less" }, { value: "scss", description: "SCSS" }, { value: "json", description: "JSON" }, { value: "json5", description: "JSON5" }, { value: "jsonc", description: "JSON with Comments" }, { value: "json-stringify", description: "JSON.stringify" }, { value: "graphql", description: "GraphQL" }, { value: "markdown", description: "Markdown" }, { value: "mdx", description: "MDX" }, { value: "vue", description: "Vue" }, { value: "yaml", description: "YAML" }, { value: "glimmer", description: "Ember / Handlebars" }, { value: "html", description: "HTML" }, { value: "angular", description: "Angular" }, { value: "lwc", description: "Lightning Web Components" }, { value: "mjml", description: "MJML" }] }, plugins: { type: "path", array: !0, default: [{ value: [] }], category: "Global", description: "Add a plugin. Multiple plugins can be passed as separate `--plugin`s.", exception: (e) => typeof e == "string" || typeof e == "object", cliName: "plugin", cliCategory: "Config" }, printWidth: { category: "Global", type: "int", default: 80, description: "The line length where Prettier will try wrap.", range: { start: 0, end: 1 / 0, step: 1 } }, rangeEnd: { category: "Special", type: "int", default: 1 / 0, range: { start: 0, end: 1 / 0, step: 1 }, description: `Format code ending at a given character offset (exclusive).
The range will extend forwards to the end of the selected statement.`, cliCategory: "Editor" }, rangeStart: { category: "Special", type: "int", default: 0, range: { start: 0, end: 1 / 0, step: 1 }, description: `Format code starting at a given character offset.
The range will extend backwards to the start of the first line containing the selected statement.`, cliCategory: "Editor" }, requirePragma: { category: "Special", type: "boolean", default: !1, description: "Require either '@prettier' or '@format' to be present in the file's first docblock comment in order for it to be formatted.", cliCategory: "Other" }, tabWidth: { type: "int", category: "Global", default: 2, description: "Number of spaces per indentation level.", range: { start: 0, end: 1 / 0, step: 1 } }, useTabs: { category: "Global", type: "boolean", default: !1, description: "Indent with tabs instead of spaces." }, embeddedLanguageFormatting: { category: "Global", type: "choice", default: "auto", description: "Control how Prettier formats quoted code embedded in the file.", choices: [{ value: "auto", description: "Format embedded code if Prettier can automatically identify it." }, { value: "off", description: "Never automatically format embedded code." }] } };
function Tp({ plugins: e = [], showDeprecated: t = !1 } = {}) {
  let n = e.flatMap((s) => s.languages ?? []), r = [];
  for (let s of Y9(Object.assign({}, ...e.map(({ options: i }) => i), W9))) !t && s.deprecated || (Array.isArray(s.choices) && (t || (s.choices = s.choices.filter((i) => !i.deprecated)), s.name === "parser" && (s.choices = [...s.choices, ...H9(s.choices, n, e)])), s.pluginDefaults = Object.fromEntries(e.filter((i) => {
    var a;
    return ((a = i.defaultOptions) == null ? void 0 : a[s.name]) !== void 0;
  }).map((i) => [i.name, i.defaultOptions[s.name]])), r.push(s));
  return { languages: n, options: r };
}
function* H9(e, t, n) {
  let r = new Set(e.map((s) => s.value));
  for (let s of t) if (s.parsers) {
    for (let i of s.parsers) if (!r.has(i)) {
      r.add(i);
      let a = n.find((l) => l.parsers && Object.prototype.hasOwnProperty.call(l.parsers, i)), o = s.name;
      a != null && a.name && (o += ` (plugin: ${a.name})`), yield { value: i, description: o };
    }
  }
}
function Y9(e) {
  let t = [];
  for (let [n, r] of Object.entries(e)) {
    let s = { name: n, ...r };
    Array.isArray(s.default) && (s.default = He(!1, s.default, -1).value), t.push(s);
  }
  return t;
}
var z9 = (e, t) => {
  if (!(e && t == null)) return t.toReversed || !Array.isArray(t) ? t.toReversed() : [...t].reverse();
}, G9 = z9, dd, md, pd, gd, yd, J9 = ((dd = globalThis.Deno) == null ? void 0 : dd.build.os) === "windows" || ((pd = (md = globalThis.navigator) == null ? void 0 : md.platform) == null ? void 0 : pd.startsWith("Win")) || ((yd = (gd = globalThis.process) == null ? void 0 : gd.platform) == null ? void 0 : yd.startsWith("win")) || !1;
function Mp(e) {
  if (e = e instanceof URL ? e : new URL(e), e.protocol !== "file:") throw new TypeError(`URL must be a file URL: received "${e.protocol}"`);
  return e;
}
function Q9(e) {
  return e = Mp(e), decodeURIComponent(e.pathname.replace(/%(?![0-9A-Fa-f]{2})/g, "%25"));
}
function K9(e) {
  e = Mp(e);
  let t = decodeURIComponent(e.pathname.replace(/\//g, "\\").replace(/%(?![0-9A-Fa-f]{2})/g, "%25")).replace(/^\\*([A-Za-z]:)(\\|$)/, "$1\\");
  return e.hostname !== "" && (t = `\\\\${e.hostname}${t}`), t;
}
function X9(e) {
  return J9 ? K9(e) : Q9(e);
}
var Z9 = X9, e7 = (e) => String(e).split(/[/\\]/u).pop();
function bd(e, t) {
  if (!t) return;
  let n = e7(t).toLowerCase();
  return e.find(({ filenames: r }) => r?.some((s) => s.toLowerCase() === n)) ?? e.find(({ extensions: r }) => r?.some((s) => n.endsWith(s)));
}
function t7(e, t) {
  if (t) return e.find(({ name: n }) => n.toLowerCase() === t) ?? e.find(({ aliases: n }) => n?.includes(t)) ?? e.find(({ extensions: n }) => n?.includes(`.${t}`));
}
function vd(e, t) {
  if (t) {
    if (String(t).startsWith("file:")) try {
      t = Z9(t);
    } catch {
      return;
    }
    if (typeof t == "string") return e.find(({ isSupported: n }) => n?.({ filepath: t }));
  }
}
function n7(e, t) {
  let n = G9(!1, e.plugins).flatMap((s) => s.languages ?? []), r = t7(n, t.language) ?? bd(n, t.physicalFile) ?? bd(n, t.file) ?? vd(n, t.physicalFile) ?? vd(n, t.file) ?? (t.physicalFile, void 0);
  return r?.parsers[0];
}
var r7 = n7, Pr = { key: (e) => /^[$_a-zA-Z][$_a-zA-Z0-9]*$/.test(e) ? e : JSON.stringify(e), value(e) {
  if (e === null || typeof e != "object") return JSON.stringify(e);
  if (Array.isArray(e)) return `[${e.map((n) => Pr.value(n)).join(", ")}]`;
  let t = Object.keys(e);
  return t.length === 0 ? "{}" : `{ ${t.map((n) => `${Pr.key(n)}: ${Pr.value(e[n])}`).join(", ")} }`;
}, pair: ({ key: e, value: t }) => Pr.value({ [e]: t }) }, Op = new Proxy(String, { get: () => Op }), zt = Op, s7 = (e, t, { descriptor: n }) => {
  let r = [`${zt.yellow(typeof e == "string" ? n.key(e) : n.pair(e))} is deprecated`];
  return t && r.push(`we now treat it as ${zt.blue(typeof t == "string" ? n.key(t) : n.pair(t))}`), r.join("; ") + ".";
}, Rp = Symbol.for("vnopts.VALUE_NOT_EXIST"), Bi = Symbol.for("vnopts.VALUE_UNCHANGED"), wd = " ".repeat(2), i7 = (e, t, n) => {
  let { text: r, list: s } = n.normalizeExpectedResult(n.schemas[e].expected(n)), i = [];
  return r && i.push(Dd(e, t, r, n.descriptor)), s && i.push([Dd(e, t, s.title, n.descriptor)].concat(s.values.map((a) => Pp(a, n.loggerPrintWidth))).join(`
`)), Ip(i, n.loggerPrintWidth);
};
function Dd(e, t, n, r) {
  return [`Invalid ${zt.red(r.key(e))} value.`, `Expected ${zt.blue(n)},`, `but received ${t === Rp ? zt.gray("nothing") : zt.red(r.value(t))}.`].join(" ");
}
function Pp({ text: e, list: t }, n) {
  let r = [];
  return e && r.push(`- ${zt.blue(e)}`), t && r.push([`- ${zt.blue(t.title)}:`].concat(t.values.map((s) => Pp(s, n - wd.length).replace(/^|\n/g, `$&${wd}`))).join(`
`)), Ip(r, n);
}
function Ip(e, t) {
  if (e.length === 1) return e[0];
  let [n, r] = e, [s, i] = e.map((a) => a.split(`
`, 1)[0].length);
  return s > t && s > i ? r : n;
}
var vo = [], Sd = [];
function a7(e, t) {
  if (e === t) return 0;
  let n = e;
  e.length > t.length && (e = t, t = n);
  let r = e.length, s = t.length;
  for (; r > 0 && e.charCodeAt(~-r) === t.charCodeAt(~-s); ) r--, s--;
  let i = 0;
  for (; i < r && e.charCodeAt(i) === t.charCodeAt(i); ) i++;
  if (r -= i, s -= i, r === 0) return s;
  let a, o, l, u, f = 0, c = 0;
  for (; f < r; ) Sd[f] = e.charCodeAt(i + f), vo[f] = ++f;
  for (; c < s; ) for (a = t.charCodeAt(i + c), l = c++, o = c, f = 0; f < r; f++) u = a === Sd[f] ? l : l + 1, l = vo[f], o = vo[f] = l > o ? u > o ? o + 1 : u : u > l ? l + 1 : u;
  return o;
}
var $p = (e, t, { descriptor: n, logger: r, schemas: s }) => {
  let i = [`Ignored unknown option ${zt.yellow(n.pair({ key: e, value: t }))}.`], a = Object.keys(s).sort().find((o) => a7(e, o) < 3);
  a && i.push(`Did you mean ${zt.blue(n.key(a))}?`), r.warn(i.join(" "));
}, o7 = ["default", "expected", "validate", "deprecated", "forward", "redirect", "overlap", "preprocess", "postprocess"];
function l7(e, t) {
  let n = new e(t), r = Object.create(n);
  for (let s of o7) s in t && (r[s] = u7(t[s], n, Bn.prototype[s].length));
  return r;
}
var Bn = class {
  static create(e) {
    return l7(this, e);
  }
  constructor(e) {
    this.name = e.name;
  }
  default(e) {
  }
  expected(e) {
    return "nothing";
  }
  validate(e, t) {
    return !1;
  }
  deprecated(e, t) {
    return !1;
  }
  forward(e, t) {
  }
  redirect(e, t) {
  }
  overlap(e, t, n) {
    return e;
  }
  preprocess(e, t) {
    return e;
  }
  postprocess(e, t) {
    return Bi;
  }
};
function u7(e, t, n) {
  return typeof e == "function" ? (...r) => e(...r.slice(0, n - 1), t, ...r.slice(n - 1)) : () => e;
}
var c7 = class extends Bn {
  constructor(e) {
    super(e), this._sourceName = e.sourceName;
  }
  expected(e) {
    return e.schemas[this._sourceName].expected(e);
  }
  validate(e, t) {
    return t.schemas[this._sourceName].validate(e, t);
  }
  redirect(e, t) {
    return this._sourceName;
  }
}, f7 = class extends Bn {
  expected() {
    return "anything";
  }
  validate() {
    return !0;
  }
}, h7 = class extends Bn {
  constructor({ valueSchema: e, name: t = e.name, ...n }) {
    super({ ...n, name: t }), this._valueSchema = e;
  }
  expected(e) {
    let { text: t, list: n } = e.normalizeExpectedResult(this._valueSchema.expected(e));
    return { text: t && `an array of ${t}`, list: n && { title: "an array of the following values", values: [{ list: n }] } };
  }
  validate(e, t) {
    if (!Array.isArray(e)) return !1;
    let n = [];
    for (let r of e) {
      let s = t.normalizeValidateResult(this._valueSchema.validate(r, t), r);
      s !== !0 && n.push(s.value);
    }
    return n.length === 0 ? !0 : { value: n };
  }
  deprecated(e, t) {
    let n = [];
    for (let r of e) {
      let s = t.normalizeDeprecatedResult(this._valueSchema.deprecated(r, t), r);
      s !== !1 && n.push(...s.map(({ value: i }) => ({ value: [i] })));
    }
    return n;
  }
  forward(e, t) {
    let n = [];
    for (let r of e) {
      let s = t.normalizeForwardResult(this._valueSchema.forward(r, t), r);
      n.push(...s.map(Ed));
    }
    return n;
  }
  redirect(e, t) {
    let n = [], r = [];
    for (let s of e) {
      let i = t.normalizeRedirectResult(this._valueSchema.redirect(s, t), s);
      "remain" in i && n.push(i.remain), r.push(...i.redirect.map(Ed));
    }
    return n.length === 0 ? { redirect: r } : { redirect: r, remain: n };
  }
  overlap(e, t) {
    return e.concat(t);
  }
};
function Ed({ from: e, to: t }) {
  return { from: [e], to: t };
}
var d7 = class extends Bn {
  expected() {
    return "true or false";
  }
  validate(e) {
    return typeof e == "boolean";
  }
};
function m7(e, t) {
  let n = /* @__PURE__ */ Object.create(null);
  for (let r of e) {
    let s = r[t];
    if (n[s]) throw new Error(`Duplicate ${t} ${JSON.stringify(s)}`);
    n[s] = r;
  }
  return n;
}
function p7(e, t) {
  let n = /* @__PURE__ */ new Map();
  for (let r of e) {
    let s = r[t];
    if (n.has(s)) throw new Error(`Duplicate ${t} ${JSON.stringify(s)}`);
    n.set(s, r);
  }
  return n;
}
function g7() {
  let e = /* @__PURE__ */ Object.create(null);
  return (t) => {
    let n = JSON.stringify(t);
    return e[n] ? !0 : (e[n] = !0, !1);
  };
}
function y7(e, t) {
  let n = [], r = [];
  for (let s of e) t(s) ? n.push(s) : r.push(s);
  return [n, r];
}
function b7(e) {
  return e === Math.floor(e);
}
function v7(e, t) {
  if (e === t) return 0;
  let n = typeof e, r = typeof t, s = ["undefined", "object", "boolean", "number", "string"];
  return n !== r ? s.indexOf(n) - s.indexOf(r) : n !== "string" ? Number(e) - Number(t) : e.localeCompare(t);
}
function w7(e) {
  return (...t) => {
    let n = e(...t);
    return typeof n == "string" ? new Error(n) : n;
  };
}
function Ad(e) {
  return e === void 0 ? {} : e;
}
function Bp(e) {
  if (typeof e == "string") return { text: e };
  let { text: t, list: n } = e;
  return D7((t || n) !== void 0, "Unexpected `expected` result, there should be at least one field."), n ? { text: t, list: { title: n.title, values: n.values.map(Bp) } } : { text: t };
}
function xd(e, t) {
  return e === !0 ? !0 : e === !1 ? { value: t } : e;
}
function Nd(e, t, n = !1) {
  return e === !1 ? !1 : e === !0 ? n ? !0 : [{ value: t }] : "value" in e ? [e] : e.length === 0 ? !1 : e;
}
function Ld(e, t) {
  return typeof e == "string" || "key" in e ? { from: t, to: e } : "from" in e ? { from: e.from, to: e.to } : { from: t, to: e.to };
}
function Hl(e, t) {
  return e === void 0 ? [] : Array.isArray(e) ? e.map((n) => Ld(n, t)) : [Ld(e, t)];
}
function kd(e, t) {
  let n = Hl(typeof e == "object" && "redirect" in e ? e.redirect : e, t);
  return n.length === 0 ? { remain: t, redirect: n } : typeof e == "object" && "remain" in e ? { remain: e.remain, redirect: n } : { redirect: n };
}
function D7(e, t) {
  if (!e) throw new Error(t);
}
var S7 = class extends Bn {
  constructor(e) {
    super(e), this._choices = p7(e.choices.map((t) => t && typeof t == "object" ? t : { value: t }), "value");
  }
  expected({ descriptor: e }) {
    let t = Array.from(this._choices.keys()).map((s) => this._choices.get(s)).filter(({ hidden: s }) => !s).map((s) => s.value).sort(v7).map(e.value), n = t.slice(0, -2), r = t.slice(-2);
    return { text: n.concat(r.join(" or ")).join(", "), list: { title: "one of the following values", values: t } };
  }
  validate(e) {
    return this._choices.has(e);
  }
  deprecated(e) {
    let t = this._choices.get(e);
    return t && t.deprecated ? { value: e } : !1;
  }
  forward(e) {
    let t = this._choices.get(e);
    return t ? t.forward : void 0;
  }
  redirect(e) {
    let t = this._choices.get(e);
    return t ? t.redirect : void 0;
  }
}, E7 = class extends Bn {
  expected() {
    return "a number";
  }
  validate(e, t) {
    return typeof e == "number";
  }
}, A7 = class extends E7 {
  expected() {
    return "an integer";
  }
  validate(e, t) {
    return t.normalizeValidateResult(super.validate(e, t), e) === !0 && b7(e);
  }
}, Cd = class extends Bn {
  expected() {
    return "a string";
  }
  validate(e) {
    return typeof e == "string";
  }
}, x7 = Pr, N7 = $p, L7 = i7, k7 = s7, C7 = class {
  constructor(e, t) {
    let { logger: n = console, loggerPrintWidth: r = 80, descriptor: s = x7, unknown: i = N7, invalid: a = L7, deprecated: o = k7, missing: l = () => !1, required: u = () => !1, preprocess: f = (d) => d, postprocess: c = () => Bi } = t || {};
    this._utils = { descriptor: s, logger: n || { warn: () => {
    } }, loggerPrintWidth: r, schemas: m7(e, "name"), normalizeDefaultResult: Ad, normalizeExpectedResult: Bp, normalizeDeprecatedResult: Nd, normalizeForwardResult: Hl, normalizeRedirectResult: kd, normalizeValidateResult: xd }, this._unknownHandler = i, this._invalidHandler = w7(a), this._deprecatedHandler = o, this._identifyMissing = (d, v) => !(d in v) || l(d, v), this._identifyRequired = u, this._preprocess = f, this._postprocess = c, this.cleanHistory();
  }
  cleanHistory() {
    this._hasDeprecationWarned = g7();
  }
  normalize(e) {
    let t = {}, n = [this._preprocess(e, this._utils)], r = () => {
      for (; n.length !== 0; ) {
        let s = n.shift(), i = this._applyNormalization(s, t);
        n.push(...i);
      }
    };
    r();
    for (let s of Object.keys(this._utils.schemas)) {
      let i = this._utils.schemas[s];
      if (!(s in t)) {
        let a = Ad(i.default(this._utils));
        "value" in a && n.push({ [s]: a.value });
      }
    }
    r();
    for (let s of Object.keys(this._utils.schemas)) {
      if (!(s in t)) continue;
      let i = this._utils.schemas[s], a = t[s], o = i.postprocess(a, this._utils);
      o !== Bi && (this._applyValidation(o, s, i), t[s] = o);
    }
    return this._applyPostprocess(t), this._applyRequiredCheck(t), t;
  }
  _applyNormalization(e, t) {
    let n = [], { knownKeys: r, unknownKeys: s } = this._partitionOptionKeys(e);
    for (let i of r) {
      let a = this._utils.schemas[i], o = a.preprocess(e[i], this._utils);
      this._applyValidation(o, i, a);
      let l = ({ from: c, to: d }) => {
        n.push(typeof d == "string" ? { [d]: c } : { [d.key]: d.value });
      }, u = ({ value: c, redirectTo: d }) => {
        let v = Nd(a.deprecated(c, this._utils), o, !0);
        if (v !== !1) if (v === !0) this._hasDeprecationWarned(i) || this._utils.logger.warn(this._deprecatedHandler(i, d, this._utils));
        else for (let { value: D } of v) {
          let S = { key: i, value: D };
          if (!this._hasDeprecationWarned(S)) {
            let x = typeof d == "string" ? { key: d, value: D } : d;
            this._utils.logger.warn(this._deprecatedHandler(S, x, this._utils));
          }
        }
      };
      Hl(a.forward(o, this._utils), o).forEach(l);
      let f = kd(a.redirect(o, this._utils), o);
      if (f.redirect.forEach(l), "remain" in f) {
        let c = f.remain;
        t[i] = i in t ? a.overlap(t[i], c, this._utils) : c, u({ value: c });
      }
      for (let { from: c, to: d } of f.redirect) u({ value: c, redirectTo: d });
    }
    for (let i of s) {
      let a = e[i];
      this._applyUnknownHandler(i, a, t, (o, l) => {
        n.push({ [o]: l });
      });
    }
    return n;
  }
  _applyRequiredCheck(e) {
    for (let t of Object.keys(this._utils.schemas)) if (this._identifyMissing(t, e) && this._identifyRequired(t)) throw this._invalidHandler(t, Rp, this._utils);
  }
  _partitionOptionKeys(e) {
    let [t, n] = y7(Object.keys(e).filter((r) => !this._identifyMissing(r, e)), (r) => r in this._utils.schemas);
    return { knownKeys: t, unknownKeys: n };
  }
  _applyValidation(e, t, n) {
    let r = xd(n.validate(e, this._utils), e);
    if (r !== !0) throw this._invalidHandler(t, r.value, this._utils);
  }
  _applyUnknownHandler(e, t, n, r) {
    let s = this._unknownHandler(e, t, this._utils);
    if (s) for (let i of Object.keys(s)) {
      if (this._identifyMissing(i, s)) continue;
      let a = s[i];
      i in this._utils.schemas ? r(i, a) : n[i] = a;
    }
  }
  _applyPostprocess(e) {
    let t = this._postprocess(e, this._utils);
    if (t !== Bi) {
      if (t.delete) for (let n of t.delete) delete e[n];
      if (t.override) {
        let { knownKeys: n, unknownKeys: r } = this._partitionOptionKeys(t.override);
        for (let s of n) {
          let i = t.override[s];
          this._applyValidation(i, s, this._utils.schemas[s]), e[s] = i;
        }
        for (let s of r) {
          let i = t.override[s];
          this._applyUnknownHandler(s, i, e, (a, o) => {
            let l = this._utils.schemas[a];
            this._applyValidation(o, a, l), e[a] = o;
          });
        }
      }
    }
  }
}, wo;
function F7(e, t, { logger: n = !1, isCLI: r = !1, passThrough: s = !1, FlagSchema: i, descriptor: a } = {}) {
  if (r) {
    if (!i) throw new Error("'FlagSchema' option is required.");
    if (!a) throw new Error("'descriptor' option is required.");
  } else a = Pr;
  let o = s ? Array.isArray(s) ? (d, v) => s.includes(d) ? { [d]: v } : void 0 : (d, v) => ({ [d]: v }) : (d, v, D) => {
    let { _: S, ...x } = D.schemas;
    return $p(d, v, { ...D, schemas: x });
  }, l = _7(t, { isCLI: r, FlagSchema: i }), u = new C7(l, { logger: n, unknown: o, descriptor: a }), f = n !== !1;
  f && wo && (u._hasDeprecationWarned = wo);
  let c = u.normalize(e);
  return f && (wo = u._hasDeprecationWarned), c;
}
function _7(e, { isCLI: t, FlagSchema: n }) {
  let r = [];
  t && r.push(f7.create({ name: "_" }));
  for (let s of e) r.push(T7(s, { isCLI: t, optionInfos: e, FlagSchema: n })), s.alias && t && r.push(c7.create({ name: s.alias, sourceName: s.name }));
  return r;
}
function T7(e, { isCLI: t, optionInfos: n, FlagSchema: r }) {
  let { name: s } = e, i = { name: s }, a, o = {};
  switch (e.type) {
    case "int":
      a = A7, t && (i.preprocess = Number);
      break;
    case "string":
      a = Cd;
      break;
    case "choice":
      a = S7, i.choices = e.choices.map((l) => l != null && l.redirect ? { ...l, redirect: { to: { key: e.name, value: l.redirect } } } : l);
      break;
    case "boolean":
      a = d7;
      break;
    case "flag":
      a = r, i.flags = n.flatMap((l) => [l.alias, l.description && l.name, l.oppositeDescription && `no-${l.name}`].filter(Boolean));
      break;
    case "path":
      a = Cd;
      break;
    default:
      throw new Error(`Unexpected type ${e.type}`);
  }
  if (e.exception ? i.validate = (l, u, f) => e.exception(l) || u.validate(l, f) : i.validate = (l, u, f) => l === void 0 || u.validate(l, f), e.redirect && (o.redirect = (l) => l ? { to: typeof e.redirect == "string" ? e.redirect : { key: e.redirect.option, value: e.redirect.value } } : void 0), e.deprecated && (o.deprecated = !0), t && !e.array) {
    let l = i.preprocess || ((u) => u);
    i.preprocess = (u, f, c) => f.preprocess(l(Array.isArray(u) ? He(!1, u, -1) : u), c);
  }
  return e.array ? h7.create({ ...t ? { preprocess: (l) => Array.isArray(l) ? l : [l] } : {}, ...o, valueSchema: a.create(i) }) : a.create({ ...i, ...o });
}
var M7 = F7, O7 = (e, t, n) => {
  if (!(e && t == null)) {
    if (t.findLast) return t.findLast(n);
    for (let r = t.length - 1; r >= 0; r--) {
      let s = t[r];
      if (n(s, r, t)) return s;
    }
  }
}, Vp = O7;
function jp(e, t) {
  if (!t) throw new Error("parserName is required.");
  let n = Vp(!1, e, (s) => s.parsers && Object.prototype.hasOwnProperty.call(s.parsers, t));
  if (n) return n;
  let r = `Couldn't resolve parser "${t}".`;
  throw r += " Plugins must be explicitly added to the standalone bundle.", new _p(r);
}
function R7(e, t) {
  if (!t) throw new Error("astFormat is required.");
  let n = Vp(!1, e, (s) => s.printers && Object.prototype.hasOwnProperty.call(s.printers, t));
  if (n) return n;
  let r = `Couldn't find plugin for AST format "${t}".`;
  throw r += " Plugins must be explicitly added to the standalone bundle.", new _p(r);
}
function Yu({ plugins: e, parser: t }) {
  let n = jp(e, t);
  return Up(n, t);
}
function Up(e, t) {
  let n = e.parsers[t];
  return typeof n == "function" ? n() : n;
}
function P7(e, t) {
  let n = e.printers[t];
  return typeof n == "function" ? n() : n;
}
var Fd = { astFormat: "estree", printer: {}, originalText: void 0, locStart: null, locEnd: null };
async function I7(e, t = {}) {
  var n;
  let r = { ...e };
  if (!r.parser) if (r.filepath) {
    if (r.parser = r7(r, { physicalFile: r.filepath }), !r.parser) throw new hd(`No parser could be inferred for file "${r.filepath}".`);
  } else throw new hd("No parser and no file path given, couldn't infer a parser.");
  let s = Tp({ plugins: e.plugins, showDeprecated: !0 }).options, i = { ...Fd, ...Object.fromEntries(s.filter((d) => d.default !== void 0).map((d) => [d.name, d.default])) }, a = jp(r.plugins, r.parser), o = await Up(a, r.parser);
  r.astFormat = o.astFormat, r.locEnd = o.locEnd, r.locStart = o.locStart;
  let l = (n = a.printers) != null && n[o.astFormat] ? a : R7(r.plugins, o.astFormat), u = await P7(l, o.astFormat);
  r.printer = u;
  let f = l.defaultOptions ? Object.fromEntries(Object.entries(l.defaultOptions).filter(([, d]) => d !== void 0)) : {}, c = { ...i, ...f };
  for (let [d, v] of Object.entries(c)) (r[d] === null || r[d] === void 0) && (r[d] = v);
  return r.parser === "json" && (r.trailingComma = "none"), M7(r, s, { passThrough: Object.keys(Fd), ...t });
}
var ms = I7, $7 = ED(ND());
async function B7(e, t) {
  let n = await Yu(t), r = n.preprocess ? n.preprocess(e, t) : e;
  t.originalText = r;
  let s;
  try {
    s = await n.parse(r, t, t);
  } catch (i) {
    V7(i, e);
  }
  return { text: r, ast: s };
}
function V7(e, t) {
  let { loc: n } = e;
  if (n) {
    let r = (0, $7.codeFrameColumns)(t, n, { highlightCode: !0 });
    throw e.message += `
` + r, e.codeFrame = r, e;
  }
  throw e;
}
var oi = B7;
async function j7(e, t, n, r, s) {
  let { embeddedLanguageFormatting: i, printer: { embed: a, hasPrettierIgnore: o = () => !1, getVisitorKeys: l } } = n;
  if (!a || i !== "auto") return;
  if (a.length > 2) throw new Error("printer.embed has too many parameters. The API changed in Prettier v3. Please update your plugin. See https://prettier.io/docs/plugins#optional-embed");
  let u = Ua(a.getVisitorKeys ?? l), f = [];
  v();
  let c = e.stack;
  for (let { print: D, node: S, pathStack: x } of f) try {
    e.stack = x;
    let N = await D(d, t, e, n);
    N && s.set(S, N);
  } catch (N) {
    if (globalThis.PRETTIER_DEBUG) throw N;
  }
  e.stack = c;
  function d(D, S) {
    return U7(D, S, n, r);
  }
  function v() {
    let { node: D } = e;
    if (D === null || typeof D != "object" || o(e)) return;
    for (let x of u(D)) Array.isArray(D[x]) ? e.each(v, x) : e.call(v, x);
    let S = a(e, n);
    if (S) {
      if (typeof S == "function") {
        f.push({ print: S, node: D, pathStack: [...e.stack] });
        return;
      }
      s.set(D, S);
    }
  }
}
async function U7(e, t, n, r) {
  let s = await ms({ ...n, ...t, parentParser: n.parser, originalText: e, cursorOffset: void 0, rangeStart: void 0, rangeEnd: void 0 }, { passThrough: !0 }), { ast: i } = await oi(e, s), a = await r(i, s);
  return gp(a);
}
function q7(e, t) {
  let { originalText: n, [Symbol.for("comments")]: r, locStart: s, locEnd: i, [Symbol.for("printedComments")]: a } = t, { node: o } = e, l = s(o), u = i(o);
  for (let f of r) s(f) >= l && i(f) <= u && a.add(f);
  return n.slice(l, u);
}
var W7 = q7;
async function qa(e, t) {
  ({ ast: e } = await qp(e, t));
  let n = /* @__PURE__ */ new Map(), r = new S9(e), s = /* @__PURE__ */ new Map();
  await j7(r, a, t, qa, s);
  let i = await _d(r, t, a, void 0, s);
  if (q9(t), t.cursorOffset >= 0) {
    if (t.nodeAfterCursor && !t.nodeBeforeCursor) return [Zn, i];
    if (t.nodeBeforeCursor && !t.nodeAfterCursor) return [i, Zn];
  }
  return i;
  function a(l, u) {
    return l === void 0 || l === r ? o(u) : Array.isArray(l) ? r.call(() => o(u), ...l) : r.call(() => o(u), l);
  }
  function o(l) {
    let u = r.node;
    if (u == null) return "";
    let f = u && typeof u == "object" && l === void 0;
    if (f && n.has(u)) return n.get(u);
    let c = _d(r, t, a, l, s);
    return f && n.set(u, c), c;
  }
}
function _d(e, t, n, r, s) {
  var i;
  let { node: a } = e, { printer: o } = t, l;
  switch ((i = o.hasPrettierIgnore) != null && i.call(o, e) ? l = W7(e, t) : s.has(a) ? l = s.get(a) : l = o.print(e, t, n, r), a) {
    case t.cursorNode:
      l = Ii(l, (u) => [Zn, u, Zn]);
      break;
    case t.nodeBeforeCursor:
      l = Ii(l, (u) => [u, Zn]);
      break;
    case t.nodeAfterCursor:
      l = Ii(l, (u) => [Zn, u]);
      break;
  }
  return o.printComment && (!o.willPrintOwnComments || !o.willPrintOwnComments(e, t)) && (l = U9(e, l, t)), l;
}
async function qp(e, t) {
  let n = e.comments ?? [];
  t[Symbol.for("comments")] = n, t[Symbol.for("printedComments")] = /* @__PURE__ */ new Set(), R9(e, t);
  let { printer: { preprocess: r } } = t;
  return e = r ? await r(e, t) : e, { ast: e, comments: n };
}
function H7(e, t) {
  let { cursorOffset: n, locStart: r, locEnd: s } = t, i = Ua(t.printer.getVisitorKeys), a = (v) => r(v) <= n && s(v) >= n, o = e, l = [e];
  for (let v of x9(e, { getVisitorKeys: i, filter: a })) l.push(v), o = v;
  if (N9(o, { getVisitorKeys: i })) return { cursorNode: o };
  let u, f, c = -1, d = Number.POSITIVE_INFINITY;
  for (; l.length > 0 && (u === void 0 || f === void 0); ) {
    o = l.pop();
    let v = u !== void 0, D = f !== void 0;
    for (let S of ja(o, { getVisitorKeys: i })) {
      if (!v) {
        let x = s(S);
        x <= n && x > c && (u = S, c = x);
      }
      if (!D) {
        let x = r(S);
        x >= n && x < d && (f = S, d = x);
      }
    }
  }
  return { nodeBeforeCursor: u, nodeAfterCursor: f };
}
var Wp = H7;
function Y7(e, t) {
  let { printer: { massageAstNode: n, getVisitorKeys: r } } = t;
  if (!n) return e;
  let s = Ua(r), i = n.ignoredProperties ?? /* @__PURE__ */ new Set();
  return a(e);
  function a(o, l) {
    if (!(o !== null && typeof o == "object")) return o;
    if (Array.isArray(o)) return o.map((d) => a(d, l)).filter(Boolean);
    let u = {}, f = new Set(s(o));
    for (let d in o) !Object.prototype.hasOwnProperty.call(o, d) || i.has(d) || (f.has(d) ? u[d] = a(o[d], o) : u[d] = o[d]);
    let c = n(o, u, l);
    if (c !== null) return c ?? u;
  }
}
var z7 = Y7, G7 = (e, t, n) => {
  if (!(e && t == null)) {
    if (t.findLastIndex) return t.findLastIndex(n);
    for (let r = t.length - 1; r >= 0; r--) {
      let s = t[r];
      if (n(s, r, t)) return r;
    }
    return -1;
  }
}, J7 = G7, Q7 = ({ parser: e }) => e === "json" || e === "json5" || e === "jsonc" || e === "json-stringify";
function K7(e, t) {
  let n = [e.node, ...e.parentNodes], r = /* @__PURE__ */ new Set([t.node, ...t.parentNodes]);
  return n.find((s) => Hp.has(s.type) && r.has(s));
}
function Td(e) {
  let t = J7(!1, e, (n) => n.type !== "Program" && n.type !== "File");
  return t === -1 ? e : e.slice(0, t + 1);
}
function X7(e, t, { locStart: n, locEnd: r }) {
  let s = e.node, i = t.node;
  if (s === i) return { startNode: s, endNode: i };
  let a = n(e.node);
  for (let l of Td(t.parentNodes)) if (n(l) >= a) i = l;
  else break;
  let o = r(t.node);
  for (let l of Td(e.parentNodes)) {
    if (r(l) <= o) s = l;
    else break;
    if (s === i) break;
  }
  return { startNode: s, endNode: i };
}
function Yl(e, t, n, r, s = [], i) {
  let { locStart: a, locEnd: o } = n, l = a(e), u = o(e);
  if (!(t > u || t < l || i === "rangeEnd" && t === l || i === "rangeStart" && t === u)) {
    for (let f of Wu(e, n)) {
      let c = Yl(f, t, n, r, [e, ...s], i);
      if (c) return c;
    }
    if (!r || r(e, s[0])) return { node: e, parentNodes: s };
  }
}
function Z7(e, t) {
  return t !== "DeclareExportDeclaration" && e !== "TypeParameterDeclaration" && (e === "Directive" || e === "TypeAlias" || e === "TSExportAssignment" || e.startsWith("Declare") || e.startsWith("TSDeclare") || e.endsWith("Statement") || e.endsWith("Declaration"));
}
var Hp = /* @__PURE__ */ new Set(["JsonRoot", "ObjectExpression", "ArrayExpression", "StringLiteral", "NumericLiteral", "BooleanLiteral", "NullLiteral", "UnaryExpression", "TemplateLiteral"]), e8 = /* @__PURE__ */ new Set(["OperationDefinition", "FragmentDefinition", "VariableDefinition", "TypeExtensionDefinition", "ObjectTypeDefinition", "FieldDefinition", "DirectiveDefinition", "EnumTypeDefinition", "EnumValueDefinition", "InputValueDefinition", "InputObjectTypeDefinition", "SchemaDefinition", "OperationTypeDefinition", "InterfaceTypeDefinition", "UnionTypeDefinition", "ScalarTypeDefinition"]);
function Md(e, t, n) {
  if (!t) return !1;
  switch (e.parser) {
    case "flow":
    case "hermes":
    case "babel":
    case "babel-flow":
    case "babel-ts":
    case "typescript":
    case "acorn":
    case "espree":
    case "meriyah":
    case "oxc":
    case "oxc-ts":
    case "__babel_estree":
      return Z7(t.type, n?.type);
    case "json":
    case "json5":
    case "jsonc":
    case "json-stringify":
      return Hp.has(t.type);
    case "graphql":
      return e8.has(t.kind);
    case "vue":
      return t.tag !== "root";
  }
  return !1;
}
function t8(e, t, n) {
  let { rangeStart: r, rangeEnd: s, locStart: i, locEnd: a } = t;
  Wl.ok(s > r);
  let o = e.slice(r, s).search(/\S/u), l = o === -1;
  if (!l) for (r += o; s > r && !/\S/u.test(e[s - 1]); --s) ;
  let u = Yl(n, r, t, (v, D) => Md(t, v, D), [], "rangeStart"), f = l ? u : Yl(n, s, t, (v) => Md(t, v), [], "rangeEnd");
  if (!u || !f) return { rangeStart: 0, rangeEnd: 0 };
  let c, d;
  if (Q7(t)) {
    let v = K7(u, f);
    c = v, d = v;
  } else ({ startNode: c, endNode: d } = X7(u, f, t));
  return { rangeStart: Math.min(i(c), i(d)), rangeEnd: Math.max(a(c), a(d)) };
}
var Yp = "\uFEFF", Od = Symbol("cursor");
async function zp(e, t, n = 0) {
  if (!e || e.trim().length === 0) return { formatted: "", cursorOffset: -1, comments: [] };
  let { ast: r, text: s } = await oi(e, t);
  t.cursorOffset >= 0 && (t = { ...t, ...Wp(r, t) });
  let i = await qa(r, t);
  n > 0 && (i = Sp([rr, i], n, t.tabWidth));
  let a = Va(i, t);
  if (n > 0) {
    let l = a.formatted.trim();
    a.cursorNodeStart !== void 0 && (a.cursorNodeStart -= a.formatted.indexOf(l), a.cursorNodeStart < 0 && (a.cursorNodeStart = 0, a.cursorNodeText = a.cursorNodeText.trimStart()), a.cursorNodeStart + a.cursorNodeText.length > l.length && (a.cursorNodeText = a.cursorNodeText.trimEnd())), a.formatted = l + Iu(t.endOfLine);
  }
  let o = t[Symbol.for("comments")];
  if (t.cursorOffset >= 0) {
    let l, u, f, c;
    if ((t.cursorNode || t.nodeBeforeCursor || t.nodeAfterCursor) && a.cursorNodeText) if (f = a.cursorNodeStart, c = a.cursorNodeText, t.cursorNode) l = t.locStart(t.cursorNode), u = s.slice(l, t.locEnd(t.cursorNode));
    else {
      if (!t.nodeBeforeCursor && !t.nodeAfterCursor) throw new Error("Cursor location must contain at least one of cursorNode, nodeBeforeCursor, nodeAfterCursor");
      l = t.nodeBeforeCursor ? t.locEnd(t.nodeBeforeCursor) : 0;
      let N = t.nodeAfterCursor ? t.locStart(t.nodeAfterCursor) : s.length;
      u = s.slice(l, N);
    }
    else l = 0, u = s, f = 0, c = a.formatted;
    let d = t.cursorOffset - l;
    if (u === c) return { formatted: a.formatted, cursorOffset: f + d, comments: o };
    let v = u.split("");
    v.splice(d, 0, Od);
    let D = c.split(""), S = TD(v, D), x = f;
    for (let N of S) if (N.removed) {
      if (N.value.includes(Od)) break;
    } else x += N.count;
    return { formatted: a.formatted, cursorOffset: x, comments: o };
  }
  return { formatted: a.formatted, cursorOffset: -1, comments: o };
}
async function n8(e, t) {
  let { ast: n, text: r } = await oi(e, t), { rangeStart: s, rangeEnd: i } = t8(r, t, n), a = r.slice(s, i), o = Math.min(s, r.lastIndexOf(`
`, s) + 1), l = r.slice(o, s).match(/^\s*/u)[0], u = Uu(l, t.tabWidth), f = await zp(a, { ...t, rangeStart: 0, rangeEnd: Number.POSITIVE_INFINITY, cursorOffset: t.cursorOffset > s && t.cursorOffset <= i ? t.cursorOffset - s : -1, endOfLine: "lf" }, u), c = f.formatted.trimEnd(), { cursorOffset: d } = t;
  d > i ? d += c.length - a.length : f.cursorOffset >= 0 && (d = f.cursorOffset + s);
  let v = r.slice(0, s) + c + r.slice(i);
  if (t.endOfLine !== "lf") {
    let D = Iu(t.endOfLine);
    d >= 0 && D === `\r
` && (d += mp(v.slice(0, d), `
`)), v = Ia(!1, v, `
`, D);
  }
  return { formatted: v, cursorOffset: d, comments: f.comments };
}
function Do(e, t, n) {
  return typeof t != "number" || Number.isNaN(t) || t < 0 || t > e.length ? n : t;
}
function Rd(e, t) {
  let { cursorOffset: n, rangeStart: r, rangeEnd: s } = t;
  return n = Do(e, n, -1), r = Do(e, r, 0), s = Do(e, s, e.length), { ...t, cursorOffset: n, rangeStart: r, rangeEnd: s };
}
function Gp(e, t) {
  let { cursorOffset: n, rangeStart: r, rangeEnd: s, endOfLine: i } = Rd(e, t), a = e.charAt(0) === Yp;
  if (a && (e = e.slice(1), n--, r--, s--), i === "auto" && (i = MD(e)), e.includes("\r")) {
    let o = (l) => mp(e.slice(0, Math.max(l, 0)), `\r
`);
    n -= o(n), r -= o(r), s -= o(s), e = OD(e);
  }
  return { hasBOM: a, text: e, options: Rd(e, { ...t, cursorOffset: n, rangeStart: r, rangeEnd: s, endOfLine: i }) };
}
async function Pd(e, t) {
  let n = await Yu(t);
  return !n.hasPragma || n.hasPragma(e);
}
async function r8(e, t) {
  var n;
  let r = await Yu(t);
  return (n = r.hasIgnorePragma) == null ? void 0 : n.call(r, e);
}
async function Jp(e, t) {
  let { hasBOM: n, text: r, options: s } = Gp(e, await ms(t));
  if (s.rangeStart >= s.rangeEnd && r !== "" || s.requirePragma && !await Pd(r, s) || s.checkIgnorePragma && await r8(r, s)) return { formatted: e, cursorOffset: t.cursorOffset, comments: [] };
  let i;
  return s.rangeStart > 0 || s.rangeEnd < r.length ? i = await n8(r, s) : (!s.requirePragma && s.insertPragma && s.printer.insertPragma && !await Pd(r, s) && (r = s.printer.insertPragma(r)), i = await zp(r, s)), n && (i.formatted = Yp + i.formatted, i.cursorOffset >= 0 && i.cursorOffset++), i;
}
async function s8(e, t, n) {
  let { text: r, options: s } = Gp(e, await ms(t)), i = await oi(r, s);
  return n && (n.preprocessForPrint && (i.ast = await qp(i.ast, s)), n.massage && (i.ast = z7(i.ast, s))), i;
}
async function i8(e, t) {
  t = await ms(t);
  let n = await qa(e, t);
  return Va(n, t);
}
async function a8(e, t) {
  let n = f9(e), { formatted: r } = await Jp(n, { ...t, parser: "__js_expression" });
  return r;
}
async function o8(e, t) {
  t = await ms(t);
  let { ast: n } = await oi(e, t);
  return t.cursorOffset >= 0 && (t = { ...t, ...Wp(n, t) }), qa(n, t);
}
async function l8(e, t) {
  return Va(e, await ms(t));
}
var Qp = {};
Pu(Qp, { builders: () => u8, printer: () => c8, utils: () => f8 });
var u8 = { join: Dp, line: vp, softline: u9, hardline: rr, literalline: wp, group: yp, conditionalGroup: r9, fill: s9, lineSuffix: Bl, lineSuffixBoundary: o9, cursor: Zn, breakParent: Ba, ifBreak: i9, trim: l9, indent: ma, indentIfBreak: a9, align: as, addAlignmentToDoc: Sp, markAsRoot: t9, dedentToRoot: e9, dedent: n9, hardlineWithoutBreakParent: Vu, literallineWithoutBreakParent: bp, label: c9, concat: (e) => e }, c8 = { printDocToString: Va }, f8 = { willBreak: qD, traverseDoc: $u, findInDoc: Bu, mapDoc: $a, removeLines: YD, stripTrailingHardline: gp, replaceEndOfLine: JD, canBreak: KD }, h8 = "3.6.2", Kp = {};
Pu(Kp, { addDanglingComment: () => Hn, addLeadingComment: () => Bs, addTrailingComment: () => Vs, getAlignmentSize: () => Uu, getIndentSize: () => b8, getMaxContinuousCount: () => D8, getNextNonSpaceNonCommentCharacter: () => E8, getNextNonSpaceNonCommentCharacterIndex: () => M8, getPreferredQuote: () => x8, getStringWidth: () => ju, hasNewline: () => On, hasNewlineInRange: () => L8, hasSpaces: () => C8, isNextLineEmpty: () => I8, isNextLineEmptyAfterIndex: () => Qu, isPreviousLineEmpty: () => R8, makeString: () => _8, skip: () => ai, skipEverythingButNewLine: () => Np, skipInlineComment: () => zu, skipNewline: () => ur, skipSpaces: () => Pn, skipToLineEnd: () => xp, skipTrailingComment: () => Gu, skipWhitespace: () => L9 });
function d8(e, t) {
  if (t === !1) return !1;
  if (e.charAt(t) === "/" && e.charAt(t + 1) === "*") {
    for (let n = t + 2; n < e.length; ++n) if (e.charAt(n) === "*" && e.charAt(n + 1) === "/") return n + 2;
  }
  return t;
}
var zu = d8;
function m8(e, t) {
  return t === !1 ? !1 : e.charAt(t) === "/" && e.charAt(t + 1) === "/" ? Np(e, t) : t;
}
var Gu = m8;
function p8(e, t) {
  let n = null, r = t;
  for (; r !== n; ) n = r, r = Pn(e, r), r = zu(e, r), r = Gu(e, r), r = ur(e, r);
  return r;
}
var Ju = p8;
function g8(e, t) {
  let n = null, r = t;
  for (; r !== n; ) n = r, r = xp(e, r), r = zu(e, r), r = Pn(e, r);
  return r = Gu(e, r), r = ur(e, r), r !== !1 && On(e, r);
}
var Qu = g8;
function y8(e, t) {
  let n = e.lastIndexOf(`
`);
  return n === -1 ? 0 : Uu(e.slice(n + 1).match(/^[\t ]*/u)[0], t);
}
var b8 = y8;
function v8(e) {
  if (typeof e != "string") throw new TypeError("Expected a string");
  return e.replace(/[|\\{}()[\]^$+*?.]/g, "\\$&").replace(/-/g, "\\x2d");
}
function w8(e, t) {
  let n = e.match(new RegExp(`(${v8(t)})+`, "gu"));
  return n === null ? 0 : n.reduce((r, s) => Math.max(r, s.length / t.length), 0);
}
var D8 = w8;
function S8(e, t) {
  let n = Ju(e, t);
  return n === !1 ? "" : e.charAt(n);
}
var E8 = S8, bi = "'", Id = '"';
function A8(e, t) {
  let n = t === !0 || t === bi ? bi : Id, r = n === bi ? Id : bi, s = 0, i = 0;
  for (let a of e) a === n ? s++ : a === r && i++;
  return s > i ? r : n;
}
var x8 = A8;
function N8(e, t, n) {
  for (let r = t; r < n; ++r) if (e.charAt(r) === `
`) return !0;
  return !1;
}
var L8 = N8;
function k8(e, t, n = {}) {
  return Pn(e, n.backwards ? t - 1 : t, n) !== t;
}
var C8 = k8;
function F8(e, t, n) {
  let r = t === '"' ? "'" : '"', s = Ia(!1, e, /\\(.)|(["'])/gsu, (i, a, o) => a === r ? a : o === t ? "\\" + o : o || (n && /^[^\n\r"'0-7\\bfnrt-vx\u2028\u2029]$/u.test(a) ? a : "\\" + a));
  return t + s + t;
}
var _8 = F8;
function T8(e, t, n) {
  return Ju(e, n(t));
}
function M8(e, t) {
  return arguments.length === 2 || typeof t == "number" ? Ju(e, t) : T8(...arguments);
}
function O8(e, t, n) {
  return Hu(e, n(t));
}
function R8(e, t) {
  return arguments.length === 2 || typeof t == "number" ? Hu(e, t) : O8(...arguments);
}
function P8(e, t, n) {
  return Qu(e, n(t));
}
function I8(e, t) {
  return arguments.length === 2 || typeof t == "number" ? Qu(e, t) : P8(...arguments);
}
function Gn(e, t = 1) {
  return async (...n) => {
    let r = n[t] ?? {}, s = r.plugins ?? [];
    return n[t] = { ...r, plugins: Array.isArray(s) ? s : Object.values(s) }, e(...n);
  };
}
var Xp = Gn(Jp);
async function Ku(e, t) {
  let { formatted: n } = await Xp(e, { ...t, cursorOffset: -1 });
  return n;
}
async function $8(e, t) {
  return await Ku(e, t) === e;
}
var B8 = Gn(Tp, 0), V8 = { parse: Gn(s8), formatAST: Gn(i8), formatDoc: Gn(a8), printToDoc: Gn(o8), printDocToString: Gn(l8) };
function Zp(e, t) {
  if (e.length < t.length)
    return !1;
  for (var n = 0; n < t.length; n++)
    if (e[n] !== t[n])
      return !1;
  return !0;
}
function zl(e, t) {
  var n = e.length - t.length;
  return n > 0 ? e.lastIndexOf(t) === n : n === 0 ? e === t : !1;
}
function j8(e) {
  return Zp(e, "(?i)") ? new RegExp(e.substring(4), "i") : new RegExp(e);
}
function Kr(e) {
  return typeof e == "boolean";
}
var ct;
(function(e) {
  e[e.Undefined = 0] = "Undefined", e[e.EnumValueMismatch = 1] = "EnumValueMismatch", e[e.Deprecated = 2] = "Deprecated", e[e.UnexpectedEndOfComment = 257] = "UnexpectedEndOfComment", e[e.UnexpectedEndOfString = 258] = "UnexpectedEndOfString", e[e.UnexpectedEndOfNumber = 259] = "UnexpectedEndOfNumber", e[e.InvalidUnicode = 260] = "InvalidUnicode", e[e.InvalidEscapeCharacter = 261] = "InvalidEscapeCharacter", e[e.InvalidCharacter = 262] = "InvalidCharacter", e[e.PropertyExpected = 513] = "PropertyExpected", e[e.CommaExpected = 514] = "CommaExpected", e[e.ColonExpected = 515] = "ColonExpected", e[e.ValueExpected = 516] = "ValueExpected", e[e.CommaOrCloseBacketExpected = 517] = "CommaOrCloseBacketExpected", e[e.CommaOrCloseBraceExpected = 518] = "CommaOrCloseBraceExpected", e[e.TrailingComma = 519] = "TrailingComma", e[e.DuplicateKey = 520] = "DuplicateKey", e[e.CommentNotPermitted = 521] = "CommentNotPermitted", e[e.SchemaResolveError = 768] = "SchemaResolveError";
})(ct || (ct = {}));
var $d;
(function(e) {
  e.LATEST = {
    textDocument: {
      completion: {
        completionItem: {
          documentationFormat: [hn.Markdown, hn.PlainText],
          commitCharactersSupport: !0
        }
      }
    }
  };
})($d || ($d = {}));
var U8 = (e, t, ...n) => n.length === 0 ? t : t.replaceAll(
  /{(\d+)}/g,
  (r, [s]) => s in n ? String(n[s]) : r
);
function ps() {
  return U8;
}
var gr = /* @__PURE__ */ (function() {
  var e = function(t, n) {
    return e = Object.setPrototypeOf || { __proto__: [] } instanceof Array && function(r, s) {
      r.__proto__ = s;
    } || function(r, s) {
      for (var i in s) Object.prototype.hasOwnProperty.call(s, i) && (r[i] = s[i]);
    }, e(t, n);
  };
  return function(t, n) {
    if (typeof n != "function" && n !== null)
      throw new TypeError("Class extends value " + String(n) + " is not a constructor or null");
    e(t, n);
    function r() {
      this.constructor = t;
    }
    t.prototype = n === null ? Object.create(n) : (r.prototype = n.prototype, new r());
  };
})(), Ns = ps();
Ns("colorHexFormatWarning", "Invalid color format. Use #RGB, #RGBA, #RRGGBB or #RRGGBBAA."), Ns("dateTimeFormatWarning", "String is not a RFC3339 date-time."), Ns("dateFormatWarning", "String is not a RFC3339 date."), Ns("timeFormatWarning", "String is not a RFC3339 time."), Ns("emailFormatWarning", "String is not an e-mail address.");
var yr = (
  /** @class */
  (function() {
    function e(t, n, r) {
      r === void 0 && (r = 0), this.offset = n, this.length = r, this.parent = t;
    }
    return Object.defineProperty(e.prototype, "children", {
      get: function() {
        return [];
      },
      enumerable: !1,
      configurable: !0
    }), e.prototype.toString = function() {
      return "type: " + this.type + " (" + this.offset + "/" + this.length + ")" + (this.parent ? " parent: {" + this.parent.toString() + "}" : "");
    }, e;
  })()
);
/** @class */
(function(e) {
  gr(t, e);
  function t(n, r) {
    var s = e.call(this, n, r) || this;
    return s.type = "null", s.value = null, s;
  }
  return t;
})(yr);
/** @class */
(function(e) {
  gr(t, e);
  function t(n, r, s) {
    var i = e.call(this, n, s) || this;
    return i.type = "boolean", i.value = r, i;
  }
  return t;
})(yr);
/** @class */
(function(e) {
  gr(t, e);
  function t(n, r) {
    var s = e.call(this, n, r) || this;
    return s.type = "array", s.items = [], s;
  }
  return Object.defineProperty(t.prototype, "children", {
    get: function() {
      return this.items;
    },
    enumerable: !1,
    configurable: !0
  }), t;
})(yr);
/** @class */
(function(e) {
  gr(t, e);
  function t(n, r) {
    var s = e.call(this, n, r) || this;
    return s.type = "number", s.isInteger = !0, s.value = Number.NaN, s;
  }
  return t;
})(yr);
/** @class */
(function(e) {
  gr(t, e);
  function t(n, r, s) {
    var i = e.call(this, n, r, s) || this;
    return i.type = "string", i.value = "", i;
  }
  return t;
})(yr);
/** @class */
(function(e) {
  gr(t, e);
  function t(n, r, s) {
    var i = e.call(this, n, r) || this;
    return i.type = "property", i.colonOffset = -1, i.keyNode = s, i;
  }
  return Object.defineProperty(t.prototype, "children", {
    get: function() {
      return this.valueNode ? [this.keyNode, this.valueNode] : [this.keyNode];
    },
    enumerable: !1,
    configurable: !0
  }), t;
})(yr);
/** @class */
(function(e) {
  gr(t, e);
  function t(n, r) {
    var s = e.call(this, n, r) || this;
    return s.type = "object", s.properties = [], s;
  }
  return Object.defineProperty(t.prototype, "children", {
    get: function() {
      return this.properties;
    },
    enumerable: !1,
    configurable: !0
  }), t;
})(yr);
function q8(e) {
  return Kr(e) ? e ? {} : { not: {} } : e;
}
var Bd;
(function(e) {
  e[e.Key = 0] = "Key", e[e.Enum = 1] = "Enum";
})(Bd || (Bd = {}));
/** @class */
(function() {
  function e() {
  }
  return Object.defineProperty(e.prototype, "schemas", {
    get: function() {
      return [];
    },
    enumerable: !1,
    configurable: !0
  }), e.prototype.add = function(t) {
  }, e.prototype.merge = function(t) {
  }, e.prototype.include = function(t) {
    return !0;
  }, e.prototype.newSub = function() {
    return this;
  }, e.instance = new e(), e;
})();
function Vi(e) {
  return Eb(e);
}
function W8(e, t) {
  if (typeof e != "string")
    throw new TypeError("Expected a string");
  for (var n = String(e), r = "", s = !!t, i = !!t, a = !1, o = t && typeof t.flags == "string" ? t.flags : "", l, u = 0, f = n.length; u < f; u++)
    switch (l = n[u], l) {
      case "/":
      case "$":
      case "^":
      case "+":
      case ".":
      case "(":
      case ")":
      case "=":
      case "!":
      case "|":
        r += "\\" + l;
        break;
      case "?":
        if (s) {
          r += ".";
          break;
        }
      case "[":
      case "]":
        if (s) {
          r += l;
          break;
        }
      case "{":
        if (s) {
          a = !0, r += "(";
          break;
        }
      case "}":
        if (s) {
          a = !1, r += ")";
          break;
        }
      case ",":
        if (a) {
          r += "|";
          break;
        }
        r += "\\" + l;
        break;
      case "*":
        for (var c = n[u - 1], d = 1; n[u + 1] === "*"; )
          d++, u++;
        var v = n[u + 1];
        if (!i)
          r += ".*";
        else {
          var D = d > 1 && (c === "/" || c === void 0 || c === "{" || c === ",") && (v === "/" || v === void 0 || v === "," || v === "}");
          D ? (v === "/" ? u++ : c === "/" && r.endsWith("\\/") && (r = r.substr(0, r.length - 2)), r += "((?:[^/]*(?:/|$))*)") : r += "([^/]*)";
        }
        break;
      default:
        r += l;
    }
  return (!o || !~o.indexOf("g")) && (r = "^" + r + "$"), new RegExp(r, o);
}
var En = ps(), H8 = "!", Y8 = "/", z8 = (
  /** @class */
  (function() {
    function e(t, n) {
      this.globWrappers = [];
      try {
        for (var r = 0, s = t; r < s.length; r++) {
          var i = s[r], a = i[0] !== H8;
          a || (i = i.substring(1)), i.length > 0 && (i[0] === Y8 && (i = i.substring(1)), this.globWrappers.push({
            regexp: W8("**/" + i, { extended: !0, globstar: !0 }),
            include: a
          }));
        }
        this.uris = n;
      } catch {
        this.globWrappers.length = 0, this.uris = [];
      }
    }
    return e.prototype.matchesPattern = function(t) {
      for (var n = !1, r = 0, s = this.globWrappers; r < s.length; r++) {
        var i = s[r], a = i.regexp, o = i.include;
        a.test(t) && (n = o);
      }
      return n;
    }, e.prototype.getURIs = function() {
      return this.uris;
    }, e;
  })()
), G8 = (
  /** @class */
  (function() {
    function e(t, n, r) {
      this.service = t, this.url = n, this.dependencies = {}, r && (this.unresolvedSchema = this.service.promise.resolve(new Rt(r)));
    }
    return e.prototype.getUnresolvedSchema = function() {
      return this.unresolvedSchema || (this.unresolvedSchema = this.service.loadSchema(this.url)), this.unresolvedSchema;
    }, e.prototype.getResolvedSchema = function() {
      var t = this;
      return this.resolvedSchema || (this.resolvedSchema = this.getUnresolvedSchema().then(function(n) {
        return t.service.resolveSchemaContent(n, t.url, t.dependencies);
      })), this.resolvedSchema;
    }, e.prototype.clearSchema = function() {
      this.resolvedSchema = void 0, this.unresolvedSchema = void 0, this.dependencies = {};
    }, e;
  })()
), Rt = (
  /** @class */
  /* @__PURE__ */ (function() {
    function e(t, n) {
      n === void 0 && (n = []), this.schema = t, this.errors = n;
    }
    return e;
  })()
), js = (
  /** @class */
  (function() {
    function e(t, n) {
      n === void 0 && (n = []), this.schema = t, this.errors = n;
    }
    return e.prototype.getSection = function(t) {
      var n = this.getSectionRecursive(t, this.schema);
      if (n)
        return q8(n);
    }, e.prototype.getSectionRecursive = function(t, n) {
      if (!n || typeof n == "boolean" || t.length === 0)
        return n;
      var r = t.shift();
      if (n.properties && typeof n.properties[r])
        return this.getSectionRecursive(t, n.properties[r]);
      if (n.patternProperties)
        for (var s = 0, i = Object.keys(n.patternProperties); s < i.length; s++) {
          var a = i[s], o = j8(a);
          if (o.test(r))
            return this.getSectionRecursive(t, n.patternProperties[a]);
        }
      else {
        if (typeof n.additionalProperties == "object")
          return this.getSectionRecursive(t, n.additionalProperties);
        if (r.match("[0-9]+")) {
          if (Array.isArray(n.items)) {
            var l = parseInt(r, 10);
            if (!isNaN(l) && n.items[l])
              return this.getSectionRecursive(t, n.items[l]);
          } else if (n.items)
            return this.getSectionRecursive(t, n.items);
        }
      }
    }, e;
  })()
), J8 = (
  /** @class */
  (function() {
    function e(t, n, r) {
      this.contextService = n, this.requestService = t, this.promiseConstructor = r || Promise, this.callOnDispose = [], this.contributionSchemas = {}, this.contributionAssociations = [], this.schemasById = {}, this.filePatternAssociations = [], this.registeredSchemasIds = {};
    }
    return e.prototype.getRegisteredSchemaIds = function(t) {
      return Object.keys(this.registeredSchemasIds).filter(function(n) {
        var r = yt.parse(n).scheme;
        return r !== "schemaservice" && (!t || t(r));
      });
    }, Object.defineProperty(e.prototype, "promise", {
      get: function() {
        return this.promiseConstructor;
      },
      enumerable: !1,
      configurable: !0
    }), e.prototype.dispose = function() {
      for (; this.callOnDispose.length > 0; )
        this.callOnDispose.pop()();
    }, e.prototype.onResourceChange = function(t) {
      var n = this;
      this.cachedSchemaForResource = void 0;
      var r = !1;
      t = An(t);
      for (var s = [t], i = Object.keys(this.schemasById).map(function(u) {
        return n.schemasById[u];
      }); s.length; )
        for (var a = s.pop(), o = 0; o < i.length; o++) {
          var l = i[o];
          l && (l.url === a || l.dependencies[a]) && (l.url !== a && s.push(l.url), l.clearSchema(), i[o] = void 0, r = !0);
        }
      return r;
    }, e.prototype.setSchemaContributions = function(t) {
      if (t.schemas) {
        var n = t.schemas;
        for (var r in n) {
          var s = An(r);
          this.contributionSchemas[s] = this.addSchemaHandle(s, n[r]);
        }
      }
      if (Array.isArray(t.schemaAssociations))
        for (var i = t.schemaAssociations, a = 0, o = i; a < o.length; a++) {
          var l = o[a], u = l.uris.map(An), f = this.addFilePatternAssociation(l.pattern, u);
          this.contributionAssociations.push(f);
        }
    }, e.prototype.addSchemaHandle = function(t, n) {
      var r = new G8(this, t, n);
      return this.schemasById[t] = r, r;
    }, e.prototype.getOrAddSchemaHandle = function(t, n) {
      return this.schemasById[t] || this.addSchemaHandle(t, n);
    }, e.prototype.addFilePatternAssociation = function(t, n) {
      var r = new z8(t, n);
      return this.filePatternAssociations.push(r), r;
    }, e.prototype.registerExternalSchema = function(t, n, r) {
      var s = An(t);
      return this.registeredSchemasIds[s] = !0, this.cachedSchemaForResource = void 0, n && this.addFilePatternAssociation(n, [t]), r ? this.addSchemaHandle(s, r) : this.getOrAddSchemaHandle(s);
    }, e.prototype.clearExternalSchemas = function() {
      this.schemasById = {}, this.filePatternAssociations = [], this.registeredSchemasIds = {}, this.cachedSchemaForResource = void 0;
      for (var t in this.contributionSchemas)
        this.schemasById[t] = this.contributionSchemas[t], this.registeredSchemasIds[t] = !0;
      for (var n = 0, r = this.contributionAssociations; n < r.length; n++) {
        var s = r[n];
        this.filePatternAssociations.push(s);
      }
    }, e.prototype.getResolvedSchema = function(t) {
      var n = An(t), r = this.schemasById[n];
      return r ? r.getResolvedSchema() : this.promise.resolve(void 0);
    }, e.prototype.loadSchema = function(t) {
      if (!this.requestService) {
        var n = En("json.schema.norequestservice", "Unable to load schema from '{0}'. No schema request service available", vi(t));
        return this.promise.resolve(new Rt({}, [n]));
      }
      return this.requestService(t).then(function(r) {
        if (!r) {
          var s = En("json.schema.nocontent", "Unable to load schema from '{0}': No content.", vi(t));
          return new Rt({}, [s]);
        }
        var i = {}, a = [];
        i = Sb(r, a);
        var o = a.length ? [En("json.schema.invalidFormat", "Unable to parse content from '{0}': Parse error at offset {1}.", vi(t), a[0].offset)] : [];
        return new Rt(i, o);
      }, function(r) {
        var s = r.toString(), i = r.toString().split("Error: ");
        return i.length > 1 && (s = i[1]), zl(s, ".") && (s = s.substr(0, s.length - 1)), new Rt({}, [En("json.schema.nocontent", "Unable to load schema from '{0}': {1}.", vi(t), s)]);
      });
    }, e.prototype.resolveSchemaContent = function(t, n, r) {
      var s = this, i = t.errors.slice(0), a = t.schema;
      if (a.$schema) {
        var o = An(a.$schema);
        if (o === "http://json-schema.org/draft-03/schema")
          return this.promise.resolve(new js({}, [En("json.schema.draft03.notsupported", "Draft-03 schemas are not supported.")]));
        o === "https://json-schema.org/draft/2019-09/schema" && i.push(En("json.schema.draft201909.notsupported", "Draft 2019-09 schemas are not yet fully supported."));
      }
      var l = this.contextService, u = function(v, D) {
        if (!D)
          return v;
        var S = v;
        return D[0] === "/" && (D = D.substr(1)), D.split("/").some(function(x) {
          return x = x.replace(/~1/g, "/").replace(/~0/g, "~"), S = S[x], !S;
        }), S;
      }, f = function(v, D, S, x) {
        var N = x ? decodeURIComponent(x) : void 0, k = u(D, N);
        if (k)
          for (var y in k)
            k.hasOwnProperty(y) && !v.hasOwnProperty(y) && (v[y] = k[y]);
        else
          i.push(En("json.schema.invalidref", "$ref '{0}' in '{1}' can not be resolved.", N, S));
      }, c = function(v, D, S, x, N) {
        l && !/^[A-Za-z][A-Za-z0-9+\-.+]*:\/\/.*/.test(D) && (D = l.resolveRelativePath(D, x)), D = An(D);
        var k = s.getOrAddSchemaHandle(D);
        return k.getUnresolvedSchema().then(function(y) {
          if (N[D] = !0, y.errors.length) {
            var b = S ? D + "#" + S : D;
            i.push(En("json.schema.problemloadingref", "Problems loading reference '{0}': {1}", b, y.errors[0]));
          }
          return f(v, y.schema, D, S), d(v, y.schema, D, k.dependencies);
        });
      }, d = function(v, D, S, x) {
        if (!v || typeof v != "object")
          return Promise.resolve(null);
        for (var N = [v], k = [], y = [], b = function() {
          for (var w = [], L = 0; L < arguments.length; L++)
            w[L] = arguments[L];
          for (var C = 0, A = w; C < A.length; C++) {
            var _ = A[C];
            typeof _ == "object" && N.push(_);
          }
        }, h = function() {
          for (var w = [], L = 0; L < arguments.length; L++)
            w[L] = arguments[L];
          for (var C = 0, A = w; C < A.length; C++) {
            var _ = A[C];
            if (typeof _ == "object")
              for (var O in _) {
                var T = O, P = _[T];
                typeof P == "object" && N.push(P);
              }
          }
        }, m = function() {
          for (var w = [], L = 0; L < arguments.length; L++)
            w[L] = arguments[L];
          for (var C = 0, A = w; C < A.length; C++) {
            var _ = A[C];
            if (Array.isArray(_))
              for (var O = 0, T = _; O < T.length; O++) {
                var P = T[O];
                typeof P == "object" && N.push(P);
              }
          }
        }, p = function(w) {
          for (var L = []; w.$ref; ) {
            var C = w.$ref, A = C.split("#", 2);
            if (delete w.$ref, A[0].length > 0) {
              y.push(c(w, A[0], A[1], S, x));
              return;
            } else
              L.indexOf(C) === -1 && (f(w, D, S, A[1]), L.push(C));
          }
          b(w.items, w.additionalItems, w.additionalProperties, w.not, w.contains, w.propertyNames, w.if, w.then, w.else), h(w.definitions, w.properties, w.patternProperties, w.dependencies), m(w.anyOf, w.allOf, w.oneOf, w.items);
        }; N.length; ) {
          var E = N.pop();
          k.indexOf(E) >= 0 || (k.push(E), p(E));
        }
        return s.promise.all(y);
      };
      return d(a, a, n, r).then(function(v) {
        return new js(a, i);
      });
    }, e.prototype.getSchemaForResource = function(t, n) {
      if (n && n.root && n.root.type === "object") {
        var r = n.root.properties.filter(function(N) {
          return N.keyNode.value === "$schema" && N.valueNode && N.valueNode.type === "string";
        });
        if (r.length > 0) {
          var s = r[0].valueNode;
          if (s && s.type === "string") {
            var i = Vi(s);
            if (i && Zp(i, ".") && this.contextService && (i = this.contextService.resolveRelativePath(i, t)), i) {
              var a = An(i);
              return this.getOrAddSchemaHandle(a).getResolvedSchema();
            }
          }
        }
      }
      if (this.cachedSchemaForResource && this.cachedSchemaForResource.resource === t)
        return this.cachedSchemaForResource.resolvedSchema;
      for (var o = /* @__PURE__ */ Object.create(null), l = [], u = K8(t), f = 0, c = this.filePatternAssociations; f < c.length; f++) {
        var d = c[f];
        if (d.matchesPattern(u))
          for (var v = 0, D = d.getURIs(); v < D.length; v++) {
            var S = D[v];
            o[S] || (l.push(S), o[S] = !0);
          }
      }
      var x = l.length > 0 ? this.createCombinedSchema(t, l).getResolvedSchema() : this.promise.resolve(void 0);
      return this.cachedSchemaForResource = { resource: t, resolvedSchema: x }, x;
    }, e.prototype.createCombinedSchema = function(t, n) {
      if (n.length === 1)
        return this.getOrAddSchemaHandle(n[0]);
      var r = "schemaservice://combinedSchema/" + encodeURIComponent(t), s = {
        allOf: n.map(function(i) {
          return { $ref: i };
        })
      };
      return this.addSchemaHandle(r, s);
    }, e.prototype.getMatchingSchemas = function(t, n, r) {
      if (r) {
        var s = r.id || "schemaservice://untitled/matchingSchemas/" + Q8++;
        return this.resolveSchemaContent(new Rt(r), s, {}).then(function(i) {
          return n.getMatchingSchemas(i.schema).filter(function(a) {
            return !a.inverted;
          });
        });
      }
      return this.getSchemaForResource(t.uri, n).then(function(i) {
        return i ? n.getMatchingSchemas(i.schema).filter(function(a) {
          return !a.inverted;
        }) : [];
      });
    }, e;
  })()
), Q8 = 0;
function An(e) {
  try {
    return yt.parse(e).toString();
  } catch {
    return e;
  }
}
function K8(e) {
  try {
    return yt.parse(e).with({ fragment: null, query: null }).toString();
  } catch {
    return e;
  }
}
function vi(e) {
  try {
    var t = yt.parse(e);
    if (t.scheme === "file")
      return t.fsPath;
  } catch {
  }
  return e;
}
function X8(e) {
  return e.replace(/[-\\{}+?|^$.,[\]()#\s]/g, "\\$&").replace(/[*]/g, ".*");
}
function Z8(e, t) {
  if (e.length < t)
    return 0;
  for (let n = 0; n < t; n++) {
    const r = e.charCodeAt(n);
    if (r !== 32 && r !== 9)
      return n;
  }
  return t;
}
function Vd(e) {
  try {
    return new RegExp(e, "u");
  } catch {
    return new RegExp(e);
  }
}
function e5(e, t) {
  t++;
  for (let n = t; n < e.length; n++) {
    const r = e.charAt(n);
    if (r === " " || r === "	")
      t++;
    else
      return t;
  }
  return t;
}
function ji(e, t) {
  if (e === t)
    return !0;
  if (e == null || t === null || t === void 0 || typeof e != typeof t || typeof e != "object" || Array.isArray(e) !== Array.isArray(t))
    return !1;
  let n, r;
  if (Array.isArray(e)) {
    if (e.length !== t.length)
      return !1;
    for (n = 0; n < e.length; n++)
      if (!ji(e[n], t[n]))
        return !1;
  } else {
    const s = [];
    for (r in e)
      s.push(r);
    s.sort();
    const i = [];
    for (r in t)
      i.push(r);
    if (i.sort(), !ji(s, i))
      return !1;
    for (n = 0; n < s.length; n++)
      if (!ji(e[s[n]], t[s[n]]))
        return !1;
  }
  return !0;
}
function wt(e) {
  return typeof e == "number";
}
function Yn(e) {
  return typeof e < "u";
}
function Ir(e) {
  return typeof e == "boolean";
}
function pa(e) {
  return typeof e == "string";
}
function t5(e) {
  return Symbol.iterator in Object(e);
}
function Gl(e) {
  const t = e.type && e.closestTitle;
  return e.title ? e.title : e.$id ? jd(e.$id) : e.$ref || e._$ref ? jd(e.$ref || e._$ref) : Array.isArray(e.type) ? e.type.join(" | ") : t ? e.type.concat("(", e.closestTitle, ")") : e.type || e.closestTitle;
}
function jd(e) {
  const t = e.match(/^(?:.*\/)?(.*?)(?:\.schema\.json)?$/);
  let n = !!t && t[1];
  return n || (n = "typeNotFound", console.error(`$ref (${e}) not parsed properly`)), n;
}
function eg(e, t) {
  const n = yt.parse(t);
  let r = nr.basename(n.fsPath);
  return nr.extname(n.fsPath) || (r += ".json"), Object.getOwnPropertyDescriptor(e, "name") ? Object.getOwnPropertyDescriptor(e, "name").value + ` (${r})` : e.title ? e.description ? e.title + " - " + e.description + ` (${r})` : e.title + ` (${r})` : r;
}
function n5(e) {
  return e.type !== "object" && !Jl(e);
}
function Jl(e) {
  return !!(e.anyOf || e.allOf || e.oneOf);
}
var r5 = ps(), s5 = (
  /** @class */
  (function() {
    function e(t, n) {
      this.jsonSchemaService = t, this.promise = n, this.validationEnabled = !0;
    }
    return e.prototype.configure = function(t) {
      t && (this.validationEnabled = t.validate !== !1, this.commentSeverity = t.allowComments ? void 0 : ce.Error);
    }, e.prototype.doValidation = function(t, n, r, s) {
      var i = this;
      if (!this.validationEnabled)
        return this.promise.resolve([]);
      var a = [], o = {}, l = function(c) {
        var d = c.range.start.line + " " + c.range.start.character + " " + c.message;
        o[d] || (o[d] = !0, a.push(c));
      }, u = function(c) {
        var d = r?.trailingCommas ? wi(r.trailingCommas) : ce.Error, v = r?.comments ? wi(r.comments) : i.commentSeverity, D = r?.schemaValidation ? wi(r.schemaValidation) : ce.Warning, S = r?.schemaRequest ? wi(r.schemaRequest) : ce.Warning;
        if (c) {
          if (c.errors.length && n.root && S) {
            var x = n.root, N = x.type === "object" ? x.properties[0] : void 0;
            if (N && N.keyNode.value === "$schema") {
              var k = N.valueNode || N, y = ie.create(t.positionAt(k.offset), t.positionAt(k.offset + k.length));
              l(bt.create(y, c.errors[0], S, ct.SchemaResolveError));
            } else {
              var y = ie.create(t.positionAt(x.offset), t.positionAt(x.offset + 1));
              l(bt.create(y, c.errors[0], S, ct.SchemaResolveError));
            }
          } else if (D) {
            var b = n.validate(t, c.schema, D);
            b && b.forEach(l);
          }
          tg(c.schema) && (v = void 0), ng(c.schema) && (d = void 0);
        }
        for (var h = 0, m = n.syntaxErrors; h < m.length; h++) {
          var p = m[h];
          if (p.code === ct.TrailingComma) {
            if (typeof d != "number")
              continue;
            p.severity = d;
          }
          l(p);
        }
        if (typeof v == "number") {
          var E = r5("InvalidCommentToken", "Comments are not permitted in JSON.");
          n.comments.forEach(function(w) {
            l(bt.create(w, E, v, ct.CommentNotPermitted));
          });
        }
        return a;
      };
      if (s) {
        var f = s.id || "schemaservice://untitled/" + i5++;
        return this.jsonSchemaService.resolveSchemaContent(new Rt(s), f, {}).then(function(c) {
          return u(c);
        });
      }
      return this.jsonSchemaService.getSchemaForResource(t.uri, n).then(function(c) {
        return u(c);
      });
    }, e;
  })()
), i5 = 0;
function tg(e) {
  if (e && typeof e == "object") {
    if (Kr(e.allowComments))
      return e.allowComments;
    if (e.allOf)
      for (var t = 0, n = e.allOf; t < n.length; t++) {
        var r = n[t], s = tg(r);
        if (Kr(s))
          return s;
      }
  }
}
function ng(e) {
  if (e && typeof e == "object") {
    if (Kr(e.allowTrailingCommas))
      return e.allowTrailingCommas;
    var t = e;
    if (Kr(t.allowsTrailingCommas))
      return t.allowsTrailingCommas;
    if (e.allOf)
      for (var n = 0, r = e.allOf; n < r.length; n++) {
        var s = r[n], i = ng(s);
        if (Kr(i))
          return i;
      }
  }
}
function wi(e) {
  switch (e) {
    case "error":
      return ce.Error;
    case "warning":
      return ce.Warning;
    case "ignore":
      return;
  }
}
var Ud = 48, a5 = 57, o5 = 65, Di = 97, l5 = 102;
function Ie(e) {
  return e < Ud ? 0 : e <= a5 ? e - Ud : (e < Di && (e += Di - o5), e >= Di && e <= l5 ? e - Di + 10 : 0);
}
function u5(e) {
  if (e[0] === "#")
    switch (e.length) {
      case 4:
        return {
          red: Ie(e.charCodeAt(1)) * 17 / 255,
          green: Ie(e.charCodeAt(2)) * 17 / 255,
          blue: Ie(e.charCodeAt(3)) * 17 / 255,
          alpha: 1
        };
      case 5:
        return {
          red: Ie(e.charCodeAt(1)) * 17 / 255,
          green: Ie(e.charCodeAt(2)) * 17 / 255,
          blue: Ie(e.charCodeAt(3)) * 17 / 255,
          alpha: Ie(e.charCodeAt(4)) * 17 / 255
        };
      case 7:
        return {
          red: (Ie(e.charCodeAt(1)) * 16 + Ie(e.charCodeAt(2))) / 255,
          green: (Ie(e.charCodeAt(3)) * 16 + Ie(e.charCodeAt(4))) / 255,
          blue: (Ie(e.charCodeAt(5)) * 16 + Ie(e.charCodeAt(6))) / 255,
          alpha: 1
        };
      case 9:
        return {
          red: (Ie(e.charCodeAt(1)) * 16 + Ie(e.charCodeAt(2))) / 255,
          green: (Ie(e.charCodeAt(3)) * 16 + Ie(e.charCodeAt(4))) / 255,
          blue: (Ie(e.charCodeAt(5)) * 16 + Ie(e.charCodeAt(6))) / 255,
          alpha: (Ie(e.charCodeAt(7)) * 16 + Ie(e.charCodeAt(8))) / 255
        };
    }
}
var c5 = (
  /** @class */
  (function() {
    function e(t) {
      this.schemaService = t;
    }
    return e.prototype.findDocumentSymbols = function(t, n, r) {
      var s = this;
      r === void 0 && (r = { resultLimit: Number.MAX_VALUE });
      var i = n.root;
      if (!i)
        return [];
      var a = r.resultLimit || Number.MAX_VALUE, o = t.uri;
      if ((o === "vscode://defaultsettings/keybindings.json" || zl(o.toLowerCase(), "/user/keybindings.json")) && i.type === "array") {
        for (var l = [], u = 0, f = i.items; u < f.length; u++) {
          var c = f[u];
          if (c.type === "object")
            for (var d = 0, v = c.properties; d < v.length; d++) {
              var D = v[d];
              if (D.keyNode.value === "key" && D.valueNode) {
                var S = ts.create(t.uri, xn(t, c));
                if (l.push({ name: Vi(D.valueNode), kind: Ut.Function, location: S }), a--, a <= 0)
                  return r && r.onResultLimitExceeded && r.onResultLimitExceeded(o), l;
              }
            }
        }
        return l;
      }
      for (var x = [
        { node: i, containerName: "" }
      ], N = 0, k = !1, y = [], b = function(m, p) {
        m.type === "array" ? m.items.forEach(function(E) {
          E && x.push({ node: E, containerName: p });
        }) : m.type === "object" && m.properties.forEach(function(E) {
          var w = E.valueNode;
          if (w)
            if (a > 0) {
              a--;
              var L = ts.create(t.uri, xn(t, E)), C = p ? p + "." + E.keyNode.value : E.keyNode.value;
              y.push({ name: s.getKeyLabel(E), kind: s.getSymbolKind(w.type), location: L, containerName: p }), x.push({ node: w, containerName: C });
            } else
              k = !0;
        });
      }; N < x.length; ) {
        var h = x[N++];
        b(h.node, h.containerName);
      }
      return k && r && r.onResultLimitExceeded && r.onResultLimitExceeded(o), y;
    }, e.prototype.findDocumentSymbols2 = function(t, n, r) {
      var s = this;
      r === void 0 && (r = { resultLimit: Number.MAX_VALUE });
      var i = n.root;
      if (!i)
        return [];
      var a = r.resultLimit || Number.MAX_VALUE, o = t.uri;
      if ((o === "vscode://defaultsettings/keybindings.json" || zl(o.toLowerCase(), "/user/keybindings.json")) && i.type === "array") {
        for (var l = [], u = 0, f = i.items; u < f.length; u++) {
          var c = f[u];
          if (c.type === "object")
            for (var d = 0, v = c.properties; d < v.length; d++) {
              var D = v[d];
              if (D.keyNode.value === "key" && D.valueNode) {
                var S = xn(t, c), x = xn(t, D.keyNode);
                if (l.push({ name: Vi(D.valueNode), kind: Ut.Function, range: S, selectionRange: x }), a--, a <= 0)
                  return r && r.onResultLimitExceeded && r.onResultLimitExceeded(o), l;
              }
            }
        }
        return l;
      }
      for (var N = [], k = [
        { node: i, result: N }
      ], y = 0, b = !1, h = function(p, E) {
        p.type === "array" ? p.items.forEach(function(w, L) {
          if (w)
            if (a > 0) {
              a--;
              var C = xn(t, w), A = C, _ = String(L), O = { name: _, kind: s.getSymbolKind(w.type), range: C, selectionRange: A, children: [] };
              E.push(O), k.push({ result: O.children, node: w });
            } else
              b = !0;
        }) : p.type === "object" && p.properties.forEach(function(w) {
          var L = w.valueNode;
          if (L)
            if (a > 0) {
              a--;
              var C = xn(t, w), A = xn(t, w.keyNode), _ = [], O = { name: s.getKeyLabel(w), kind: s.getSymbolKind(L.type), range: C, selectionRange: A, children: _, detail: s.getDetail(L) };
              E.push(O), k.push({ result: _, node: L });
            } else
              b = !0;
        });
      }; y < k.length; ) {
        var m = k[y++];
        h(m.node, m.result);
      }
      return b && r && r.onResultLimitExceeded && r.onResultLimitExceeded(o), N;
    }, e.prototype.getSymbolKind = function(t) {
      switch (t) {
        case "object":
          return Ut.Module;
        case "string":
          return Ut.String;
        case "number":
          return Ut.Number;
        case "array":
          return Ut.Array;
        case "boolean":
          return Ut.Boolean;
        default:
          return Ut.Variable;
      }
    }, e.prototype.getKeyLabel = function(t) {
      var n = t.keyNode.value;
      return n && (n = n.replace(/[\n]/g, "↵")), n && n.trim() ? n : '"' + n + '"';
    }, e.prototype.getDetail = function(t) {
      if (t) {
        if (t.type === "boolean" || t.type === "number" || t.type === "null" || t.type === "string")
          return String(t.value);
        if (t.type === "array")
          return t.children.length ? void 0 : "[]";
        if (t.type === "object")
          return t.children.length ? void 0 : "{}";
      }
    }, e.prototype.findDocumentColors = function(t, n, r) {
      return this.schemaService.getSchemaForResource(t.uri, n).then(function(s) {
        var i = [];
        if (s)
          for (var a = r && typeof r.resultLimit == "number" ? r.resultLimit : Number.MAX_VALUE, o = n.getMatchingSchemas(s.schema), l = {}, u = 0, f = o; u < f.length; u++) {
            var c = f[u];
            if (!c.inverted && c.schema && (c.schema.format === "color" || c.schema.format === "color-hex") && c.node && c.node.type === "string") {
              var d = String(c.node.offset);
              if (!l[d]) {
                var v = u5(Vi(c.node));
                if (v) {
                  var D = xn(t, c.node);
                  i.push({ color: v, range: D });
                }
                if (l[d] = !0, a--, a <= 0)
                  return r && r.onResultLimitExceeded && r.onResultLimitExceeded(t.uri), i;
              }
            }
          }
        return i;
      });
    }, e.prototype.getColorPresentations = function(t, n, r, s) {
      var i = [], a = Math.round(r.red * 255), o = Math.round(r.green * 255), l = Math.round(r.blue * 255);
      function u(c) {
        var d = c.toString(16);
        return d.length !== 2 ? "0" + d : d;
      }
      var f;
      return r.alpha === 1 ? f = "#" + u(a) + u(o) + u(l) : f = "#" + u(a) + u(o) + u(l) + u(Math.round(r.alpha * 255)), i.push({ label: f, textEdit: _e.replace(s, JSON.stringify(f)) }), i;
    }, e;
  })()
);
function xn(e, t) {
  return ie.create(e.positionAt(t.offset), e.positionAt(t.offset + t.length));
}
function f5(e, t) {
  var n = [];
  return t.visit(function(r) {
    var s;
    if (r.type === "property" && r.keyNode.value === "$ref" && ((s = r.valueNode) === null || s === void 0 ? void 0 : s.type) === "string") {
      var i = r.valueNode.value, a = d5(t, i);
      if (a) {
        var o = e.positionAt(a.offset);
        n.push({
          target: e.uri + "#" + (o.line + 1) + "," + (o.character + 1),
          range: h5(e, r.valueNode)
        });
      }
    }
    return !0;
  }), Promise.resolve(n);
}
function h5(e, t) {
  return ie.create(e.positionAt(t.offset + 1), e.positionAt(t.offset + t.length - 1));
}
function d5(e, t) {
  var n = m5(t);
  return n ? Ql(n, e.root) : null;
}
function Ql(e, t) {
  if (!t)
    return null;
  if (e.length === 0)
    return t;
  var n = e.shift();
  if (t && t.type === "object") {
    var r = t.properties.find(function(a) {
      return a.keyNode.value === n;
    });
    return r ? Ql(e, r.valueNode) : null;
  } else if (t && t.type === "array" && n.match(/^(0|[1-9][0-9]*)$/)) {
    var s = Number.parseInt(n), i = t.items[s];
    return i ? Ql(e, i) : null;
  }
  return null;
}
function m5(e) {
  return e === "#" ? [] : e[0] !== "#" || e[1] !== "/" ? null : e.substring(2).split(/\//).map(p5);
}
function p5(e) {
  return e.replace(/~1/g, "/").replace(/~0/g, "~");
}
function Wa(e, t) {
  for (const n of t.documents)
    if (n.internalDocument && n.internalDocument.range[0] <= e && n.internalDocument.range[2] >= e)
      return n;
  return t.documents.length === 1 ? t.documents[0] : null;
}
function rg(e) {
  const t = ["mapping", "scalar", "sequence"];
  return e ? e.filter((n) => {
    if (typeof n == "string") {
      const r = n.split(" "), s = r[1] && r[1].toLowerCase() || "scalar";
      return s === "map" ? !1 : t.indexOf(s) !== -1;
    }
    return !1;
  }) : [];
}
function sg(e, t) {
  if (!t || !e || t.length !== e.length)
    return !1;
  for (let n = e.length - 1; n >= 0; n--)
    if (e[n] !== t[n])
      return !1;
  return !0;
}
function g5(e, t) {
  const n = (e.toString().split(".")[1] || "").length, r = (t.toString().split(".")[1] || "").length, s = Math.max(n, r), i = parseInt(e.toFixed(s).replace(".", "")), a = parseInt(t.toFixed(s).replace(".", ""));
  return i % a / Math.pow(10, s);
}
var me = ps(), So = "Property {0} is not allowed.", y5 = {
  "color-hex": {
    errorMessage: me("colorHexFormatWarning", "Invalid color format. Use #RGB, #RGBA, #RRGGBB or #RRGGBBAA."),
    pattern: /^#([0-9A-Fa-f]{3,4}|([0-9A-Fa-f]{2}){3,4})$/
  },
  "date-time": {
    errorMessage: me("dateTimeFormatWarning", "String is not a RFC3339 date-time."),
    pattern: /^(\d{4})-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9]|60)(\.[0-9]+)?(Z|(\+|-)([01][0-9]|2[0-3]):([0-5][0-9]))$/i
  },
  date: {
    errorMessage: me("dateFormatWarning", "String is not a RFC3339 date."),
    pattern: /^(\d{4})-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$/i
  },
  time: {
    errorMessage: me("timeFormatWarning", "String is not a RFC3339 time."),
    pattern: /^([01][0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9]|60)(\.[0-9]+)?(Z|(\+|-)([01][0-9]|2[0-3]):([0-5][0-9]))$/i
  },
  email: {
    errorMessage: me("emailFormatWarning", "String is not an e-mail address."),
    pattern: /^(([^<>()[\]\\.,;:\s@"]+(\.[^<>()[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/
  },
  ipv4: {
    errorMessage: me("ipv4FormatWarning", "String does not match IPv4 format."),
    pattern: /^((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\b){4}$/
  },
  ipv6: {
    errorMessage: me("ipv6FormatWarning", "String does not match IPv6 format."),
    pattern: /^([0-9a-f]|:){1,4}(:([0-9a-f]{0,4})*){1,7}$/i
  }
}, Ha = "YAML", ig = "yaml-schema: ", Xe;
(function(e) {
  e.missingRequiredPropWarning = "missingRequiredPropWarning", e.typeMismatchWarning = "typeMismatchWarning", e.constWarning = "constWarning";
})(Xe || (Xe = {}));
var b5 = {
  [Xe.missingRequiredPropWarning]: 'Missing property "{0}".',
  [Xe.typeMismatchWarning]: 'Incorrect type. Expected "{0}".',
  [Xe.constWarning]: "Value must be {0}."
}, br = class {
  constructor(e, t, n, r) {
    this.offset = n, this.length = r, this.parent = e, this.internalNode = t;
  }
  getNodeFromOffsetEndInclusive(e) {
    const t = [], n = (a) => {
      if (e >= a.offset && e <= a.offset + a.length) {
        const o = a.children;
        for (let l = 0; l < o.length && o[l].offset <= e; l++) {
          const u = n(o[l]);
          u && t.push(u);
        }
        return a;
      }
      return null;
    }, r = n(this);
    let s = Number.MAX_VALUE, i = null;
    for (const a of t) {
      const o = a.length + a.offset - e + (e - a.offset);
      o < s && (i = a, s = o);
    }
    return i || r;
  }
  get children() {
    return [];
  }
  toString() {
    return "type: " + this.type + " (" + this.offset + "/" + this.length + ")" + (this.parent ? " parent: {" + this.parent.toString() + "}" : "");
  }
}, v5 = class extends br {
  constructor(e, t, n, r) {
    super(e, t, n, r), this.type = "null", this.value = null;
  }
}, w5 = class extends br {
  constructor(e, t, n, r, s, i) {
    super(e, t, s, i), this.type = "boolean", this.value = n, this.source = r;
  }
}, D5 = class extends br {
  constructor(e, t, n, r) {
    super(e, t, n, r), this.type = "array", this.items = [];
  }
  get children() {
    return this.items;
  }
}, S5 = class extends br {
  constructor(e, t, n, r) {
    super(e, t, n, r), this.type = "number", this.isInteger = !0, this.value = Number.NaN;
  }
}, ga = class extends br {
  constructor(e, t, n, r) {
    super(e, t, n, r), this.type = "string", this.value = "";
  }
}, E5 = class extends br {
  constructor(e, t, n, r) {
    super(e, t, n, r), this.type = "property", this.colonOffset = -1;
  }
  get children() {
    return this.valueNode ? [this.keyNode, this.valueNode] : [this.keyNode];
  }
}, A5 = class extends br {
  constructor(e, t, n, r) {
    super(e, t, n, r), this.type = "object", this.properties = [];
  }
  get children() {
    return this.properties;
  }
};
function Qe(e) {
  if (e !== void 0)
    return Ir(e) ? e ? {} : { not: {} } : (typeof e != "object" && (console.warn(`Wrong schema: ${JSON.stringify(e)}, it MUST be an Object or Boolean`), e = {
      type: e
    }), e);
}
var qd;
(function(e) {
  e[e.Key = 0] = "Key", e[e.Enum = 1] = "Enum";
})(qd || (qd = {}));
var x5 = class ag {
  constructor(t = -1, n = null) {
    this.focusOffset = t, this.exclude = n, this.schemas = [];
  }
  add(t) {
    this.schemas.push(t);
  }
  merge(t) {
    this.schemas.push(...t.schemas);
  }
  include(t) {
    return (this.focusOffset === -1 || og(t, this.focusOffset)) && t !== this.exclude;
  }
  newSub() {
    return new ag(-1, this.exclude);
  }
}, Zs = class {
  constructor() {
  }
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  get schemas() {
    return [];
  }
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  add(e) {
  }
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  merge(e) {
  }
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  include(e) {
    return !0;
  }
  newSub() {
    return this;
  }
};
Zs.instance = new Zs();
var it = class {
  constructor(e) {
    this.problems = [], this.propertiesMatches = 0, this.propertiesValueMatches = 0, this.primaryValueMatches = 0, this.enumValueMatch = !1, e ? this.enumValues = [] : this.enumValues = null;
  }
  hasProblems() {
    return !!this.problems.length;
  }
  mergeAll(e) {
    for (const t of e)
      this.merge(t);
  }
  merge(e) {
    this.problems = this.problems.concat(e.problems);
  }
  mergeEnumValues(e) {
    if (!this.enumValueMatch && !e.enumValueMatch && this.enumValues && e.enumValues) {
      this.enumValues = this.enumValues.concat(e.enumValues);
      for (const t of this.problems)
        t.code === ct.EnumValueMismatch && (t.message = me("enumWarning", "Value is not accepted. Valid values: {0}.", [...new Set(this.enumValues)].map((n) => JSON.stringify(n)).join(", ")));
    }
  }
  /**
   * Merge multiple warnings with same problemType together
   * @param subValidationResult another possible result
   */
  mergeWarningGeneric(e, t) {
    var n, r, s;
    if ((n = this.problems) != null && n.length)
      for (const i of t) {
        const a = this.problems.filter((o) => o.problemType === i);
        for (const o of a) {
          const l = (r = e.problems) == null ? void 0 : r.find(
            (u) => u.problemType === i && o.location.offset === u.location.offset && (i !== Xe.missingRequiredPropWarning || sg(u.problemArgs, o.problemArgs))
          );
          l && ((s = l.problemArgs) != null && s.length && (l.problemArgs.filter((u) => !o.problemArgs.includes(u)).forEach((u) => o.problemArgs.push(u)), o.message = Ui(o.problemType, o.problemArgs)), this.mergeSources(l, o));
        }
      }
  }
  mergePropertyMatch(e) {
    this.merge(e), this.propertiesMatches++, (e.enumValueMatch || !e.hasProblems() && e.propertiesMatches) && this.propertiesValueMatches++, e.enumValueMatch && e.enumValues && this.primaryValueMatches++;
  }
  mergeSources(e, t) {
    const n = e.source.replace(ig, "");
    t.source.includes(n) || (t.source = t.source + " | " + n), t.schemaUri.includes(e.schemaUri[0]) || (t.schemaUri = t.schemaUri.concat(e.schemaUri));
  }
  compareGeneric(e) {
    const t = this.hasProblems();
    return t !== e.hasProblems() ? t ? -1 : 1 : this.enumValueMatch !== e.enumValueMatch ? e.enumValueMatch ? -1 : 1 : this.propertiesValueMatches !== e.propertiesValueMatches ? this.propertiesValueMatches - e.propertiesValueMatches : this.primaryValueMatches !== e.primaryValueMatches ? this.primaryValueMatches - e.primaryValueMatches : this.propertiesMatches - e.propertiesMatches;
  }
  compareKubernetes(e) {
    const t = this.hasProblems();
    return this.propertiesMatches !== e.propertiesMatches ? this.propertiesMatches - e.propertiesMatches : this.enumValueMatch !== e.enumValueMatch ? e.enumValueMatch ? -1 : 1 : this.primaryValueMatches !== e.primaryValueMatches ? this.primaryValueMatches - e.primaryValueMatches : this.propertiesValueMatches !== e.propertiesValueMatches ? this.propertiesValueMatches - e.propertiesValueMatches : t !== e.hasProblems() ? t ? -1 : 1 : this.propertiesMatches - e.propertiesMatches;
  }
};
function Us(e) {
  switch (e.type) {
    case "array":
      return e.children.map(Us);
    case "object": {
      const t = /* @__PURE__ */ Object.create(null);
      for (let n = 0, r = e.children; n < r.length; n++) {
        const s = r[n], i = s.children[1];
        i && (t[s.children[0].value] = Us(i));
      }
      return t;
    }
    case "null":
    case "string":
    case "number":
      return e.value;
    case "boolean":
      return e.source;
    default:
      return;
  }
}
function og(e, t, n = !1) {
  return t >= e.offset && t <= e.offset + e.length || n && t === e.offset + e.length;
}
function lg(e, t, n) {
  if (n === void 0 && (n = !1), og(e, t, n)) {
    const r = e.children;
    if (Array.isArray(r))
      for (let s = 0; s < r.length && r[s].offset <= t; s++) {
        const i = lg(r[s], t, n);
        if (i)
          return i;
      }
    return e;
  }
}
var N5 = class {
  constructor(e, t = [], n = []) {
    this.root = e, this.syntaxErrors = t, this.comments = n;
  }
  getNodeFromOffset(e, t = !1) {
    if (this.root)
      return lg(this.root, e, t);
  }
  getNodeFromOffsetEndInclusive(e) {
    return this.root && this.root.getNodeFromOffsetEndInclusive(e);
  }
  visit(e) {
    if (this.root) {
      const t = (n) => {
        let r = e(n);
        const s = n.children;
        if (Array.isArray(s))
          for (let i = 0; i < s.length && r; i++)
            r = t(s[i]);
        return r;
      };
      t(this.root);
    }
  }
  validate(e, t) {
    if (this.root && t) {
      const n = new it(this.isKubernetes);
      return qe(this.root, t, t, n, Zs.instance, {
        isKubernetes: this.isKubernetes,
        disableAdditionalProperties: this.disableAdditionalProperties,
        uri: this.uri
      }), n.problems.map((r) => {
        const s = ie.create(e.positionAt(r.location.offset), e.positionAt(r.location.offset + r.location.length)), i = bt.create(s, r.message, r.severity, r.code ? r.code : ct.Undefined, r.source);
        return i.data = { schemaUri: r.schemaUri, ...r.data }, i;
      });
    }
    return null;
  }
  /**
   * This method returns the list of applicable schemas
   *
   * currently used @param didCallFromAutoComplete flag to differentiate the method call, when it is from auto complete
   * then user still types something and skip the validation for timebeing untill completed.
   * On https://github.com/redhat-developer/yaml-language-server/pull/719 the auto completes need to populate the list of enum string which matches to the enum
   * and on https://github.com/redhat-developer/vscode-yaml/issues/803 the validation should throw the error based on the enum string.
   *
   * @param schema schema
   * @param focusOffset  offsetValue
   * @param exclude excluded Node
   * @param didCallFromAutoComplete true if method called from AutoComplete
   * @returns array of applicable schemas
   */
  getMatchingSchemas(e, t = -1, n = null, r) {
    const s = new x5(t, n);
    return this.root && e && qe(this.root, e, e, new it(this.isKubernetes), s, {
      isKubernetes: this.isKubernetes,
      disableAdditionalProperties: this.disableAdditionalProperties,
      uri: this.uri,
      callFromAutoComplete: r
    }), s.schemas;
  }
};
function qe(e, t, n, r, s, i) {
  const { isKubernetes: a, callFromAutoComplete: o } = i;
  if (!e || typeof t != "object")
    return;
  switch (t.url || (t.url = n.url), t.closestTitle = t.title || n.closestTitle, e.type) {
    case "object":
      d(e, t, r, s);
      break;
    case "array":
      c(e, t, r, s);
      break;
    case "string":
      f(e, t, r);
      break;
    case "number":
      u(e, t, r);
      break;
    case "property":
      return qe(e.valueNode, t, t, r, s, i);
  }
  l(), s.add({ node: e, schema: t });
  function l() {
    function x(m) {
      return e.type === m || m === "integer" && e.type === "number" && e.isInteger;
    }
    if (Array.isArray(t.type))
      t.type.some(x) || r.problems.push({
        location: { offset: e.offset, length: e.length },
        severity: ce.Warning,
        message: t.errorMessage || me("typeArrayMismatchWarning", "Incorrect type. Expected one of {0}.", t.type.join(", ")),
        source: Se(t, n),
        schemaUri: Ee(t, n)
      });
    else if (t.type && !x(t.type)) {
      const m = t.type === "object" ? Gl(t) : t.type;
      r.problems.push({
        location: { offset: e.offset, length: e.length },
        severity: ce.Warning,
        message: t.errorMessage || Ui(Xe.typeMismatchWarning, [m]),
        source: Se(t, n),
        schemaUri: Ee(t, n),
        problemType: Xe.typeMismatchWarning,
        problemArgs: [m]
      });
    }
    if (Array.isArray(t.allOf))
      for (const m of t.allOf)
        qe(e, Qe(m), t, r, s, i);
    const N = Qe(t.not);
    if (N) {
      const m = new it(a), p = s.newSub();
      qe(e, N, t, m, p, i), m.hasProblems() || r.problems.push({
        location: { offset: e.offset, length: e.length },
        severity: ce.Warning,
        message: me("notSchemaWarning", "Matches a schema that is not allowed."),
        source: Se(t, n),
        schemaUri: Ee(t, n)
      });
      for (const E of p.schemas)
        E.inverted = !E.inverted, s.add(E);
    }
    const k = (m, p) => {
      var E;
      const w = [], L = [], C = [];
      let A = null;
      for (const _ of m) {
        const O = { ...Qe(_) }, T = new it(a), P = s.newSub();
        qe(e, O, t, T, P, i), (!T.hasProblems() || o) && (w.push(O), L.push(O), T.propertiesMatches === 0 && C.push(O), O.format && L.pop()), A ? a ? A = v(T, A, O, P) : A = D(e, p, T, A, O, P) : A = {
          schema: O,
          validationResult: T,
          matchingSchemas: P
        };
      }
      return L.length > 1 && (L.length > 1 || C.length === 0) && p && r.problems.push({
        location: { offset: e.offset, length: 1 },
        severity: ce.Warning,
        message: me("oneOfWarning", "Matches multiple schemas when only one must validate."),
        source: Se(t, n),
        schemaUri: Ee(t, n)
      }), A !== null && (r.merge(A.validationResult), r.propertiesMatches += A.validationResult.propertiesMatches, r.propertiesValueMatches += A.validationResult.propertiesValueMatches, r.enumValueMatch = r.enumValueMatch || A.validationResult.enumValueMatch, (E = A.validationResult.enumValues) != null && E.length && (r.enumValues = (r.enumValues || []).concat(A.validationResult.enumValues)), s.merge(A.matchingSchemas)), w.length;
    };
    Array.isArray(t.anyOf) && k(t.anyOf, !1), Array.isArray(t.oneOf) && k(t.oneOf, !0);
    const y = (m, p) => {
      const E = new it(a), w = s.newSub();
      qe(e, Qe(m), p, E, w, i), r.merge(E), r.propertiesMatches += E.propertiesMatches, r.propertiesValueMatches += E.propertiesValueMatches, s.merge(w);
    }, b = (m, p, E, w) => {
      const L = Qe(m), C = new it(a), A = s.newSub();
      qe(e, L, p, C, A, i), s.merge(A);
      const { filePatternAssociation: _ } = L;
      _ && (new G5(_).matchesPattern(i.uri) || C.problems.push({
        location: { offset: e.offset, length: e.length },
        severity: ce.Warning,
        message: me("ifFilePatternAssociation", `filePatternAssociation '${_}' does not match with doc uri '${i.uri}'.`),
        source: Se(t, p),
        schemaUri: Ee(t, p)
      })), C.hasProblems() ? w && y(w, p) : E && y(E, p);
    }, h = Qe(t.if);
    if (h && b(h, t, Qe(t.then), Qe(t.else)), Array.isArray(t.enum)) {
      const m = Us(e);
      let p = !1;
      for (const E of t.enum)
        if (m === E || Wd(o, e, m, E)) {
          p = !0;
          break;
        }
      r.enumValues = t.enum, r.enumValueMatch = p, p || r.problems.push({
        location: { offset: e.offset, length: e.length },
        severity: ce.Warning,
        code: ct.EnumValueMismatch,
        message: t.errorMessage || me("enumWarning", "Value is not accepted. Valid values: {0}.", t.enum.map((E) => JSON.stringify(E)).join(", ")),
        source: Se(t, n),
        schemaUri: Ee(t, n),
        data: { values: t.enum }
      });
    }
    if (Yn(t.const)) {
      const m = Us(e);
      !ji(m, t.const) && !Wd(o, e, m, t.const) ? (r.problems.push({
        location: { offset: e.offset, length: e.length },
        severity: ce.Warning,
        code: ct.EnumValueMismatch,
        problemType: Xe.constWarning,
        message: t.errorMessage || Ui(Xe.constWarning, [JSON.stringify(t.const)]),
        source: Se(t, n),
        schemaUri: Ee(t, n),
        problemArgs: [JSON.stringify(t.const)],
        data: { values: [t.const] }
      }), r.enumValueMatch = !1) : r.enumValueMatch = !0, r.enumValues = [t.const];
    }
    t.deprecationMessage && e.parent && r.problems.push({
      location: { offset: e.parent.offset, length: e.parent.length },
      severity: ce.Warning,
      message: t.deprecationMessage,
      source: Se(t, n),
      schemaUri: Ee(t, n)
    });
  }
  function u(x, N, k) {
    const y = x.value;
    wt(N.multipleOf) && g5(y, N.multipleOf) !== 0 && k.problems.push({
      location: { offset: x.offset, length: x.length },
      severity: ce.Warning,
      message: me("multipleOfWarning", "Value is not divisible by {0}.", N.multipleOf),
      source: Se(N, n),
      schemaUri: Ee(N, n)
    });
    function b(L, C) {
      if (wt(C))
        return C;
      if (Ir(C) && C)
        return L;
    }
    function h(L, C) {
      if (!Ir(C) || !C)
        return L;
    }
    const m = b(N.minimum, N.exclusiveMinimum);
    wt(m) && y <= m && k.problems.push({
      location: { offset: x.offset, length: x.length },
      severity: ce.Warning,
      message: me("exclusiveMinimumWarning", "Value is below the exclusive minimum of {0}.", m),
      source: Se(N, n),
      schemaUri: Ee(N, n)
    });
    const p = b(N.maximum, N.exclusiveMaximum);
    wt(p) && y >= p && k.problems.push({
      location: { offset: x.offset, length: x.length },
      severity: ce.Warning,
      message: me("exclusiveMaximumWarning", "Value is above the exclusive maximum of {0}.", p),
      source: Se(N, n),
      schemaUri: Ee(N, n)
    });
    const E = h(N.minimum, N.exclusiveMinimum);
    wt(E) && y < E && k.problems.push({
      location: { offset: x.offset, length: x.length },
      severity: ce.Warning,
      message: me("minimumWarning", "Value is below the minimum of {0}.", E),
      source: Se(N, n),
      schemaUri: Ee(N, n)
    });
    const w = h(N.maximum, N.exclusiveMaximum);
    wt(w) && y > w && k.problems.push({
      location: { offset: x.offset, length: x.length },
      severity: ce.Warning,
      message: me("maximumWarning", "Value is above the maximum of {0}.", w),
      source: Se(N, n),
      schemaUri: Ee(N, n)
    });
  }
  function f(x, N, k) {
    if (wt(N.minLength) && x.value.length < N.minLength && k.problems.push({
      location: { offset: x.offset, length: x.length },
      severity: ce.Warning,
      message: me("minLengthWarning", "String is shorter than the minimum length of {0}.", N.minLength),
      source: Se(N, n),
      schemaUri: Ee(N, n)
    }), wt(N.maxLength) && x.value.length > N.maxLength && k.problems.push({
      location: { offset: x.offset, length: x.length },
      severity: ce.Warning,
      message: me("maxLengthWarning", "String is longer than the maximum length of {0}.", N.maxLength),
      source: Se(N, n),
      schemaUri: Ee(N, n)
    }), pa(N.pattern) && (Vd(N.pattern).test(x.value) || k.problems.push({
      location: { offset: x.offset, length: x.length },
      severity: ce.Warning,
      message: N.patternErrorMessage || N.errorMessage || me("patternWarning", 'String does not match the pattern of "{0}".', N.pattern),
      source: Se(N, n),
      schemaUri: Ee(N, n)
    })), N.format)
      switch (N.format) {
        case "uri":
        case "uri-reference":
          {
            let y;
            if (!x.value)
              y = me("uriEmpty", "URI expected.");
            else
              try {
                !yt.parse(x.value).scheme && N.format === "uri" && (y = me("uriSchemeMissing", "URI with a scheme is expected."));
              } catch (b) {
                y = b.message;
              }
            y && k.problems.push({
              location: { offset: x.offset, length: x.length },
              severity: ce.Warning,
              message: N.patternErrorMessage || N.errorMessage || me("uriFormatWarning", "String is not a URI: {0}", y),
              source: Se(N, n),
              schemaUri: Ee(N, n)
            });
          }
          break;
        case "color-hex":
        case "date-time":
        case "date":
        case "time":
        case "email":
        case "ipv4":
        case "ipv6":
          {
            const y = y5[N.format];
            (!x.value || !y.pattern.test(x.value)) && k.problems.push({
              location: { offset: x.offset, length: x.length },
              severity: ce.Warning,
              message: N.patternErrorMessage || N.errorMessage || y.errorMessage,
              source: Se(N, n),
              schemaUri: Ee(N, n)
            });
          }
          break;
      }
  }
  function c(x, N, k, y) {
    if (Array.isArray(N.items)) {
      const h = N.items;
      for (let m = 0; m < h.length; m++) {
        const p = h[m], E = Qe(p), w = new it(a), L = x.items[m];
        L ? (qe(L, E, N, w, y, i), k.mergePropertyMatch(w), k.mergeEnumValues(w)) : x.items.length >= h.length && k.propertiesValueMatches++;
      }
      if (x.items.length > h.length)
        if (typeof N.additionalItems == "object")
          for (let m = h.length; m < x.items.length; m++) {
            const p = new it(a);
            qe(x.items[m], N.additionalItems, N, p, y, i), k.mergePropertyMatch(p), k.mergeEnumValues(p);
          }
        else N.additionalItems === !1 && k.problems.push({
          location: { offset: x.offset, length: x.length },
          severity: ce.Warning,
          message: me("additionalItemsWarning", "Array has too many items according to schema. Expected {0} or fewer.", h.length),
          source: Se(N, n),
          schemaUri: Ee(N, n)
        });
    } else {
      const h = Qe(N.items);
      if (h) {
        const m = new it(a);
        x.items.forEach((p) => {
          if (h.oneOf && h.oneOf.length === 1) {
            const E = h.oneOf[0], w = { ...Qe(E) };
            w.title = N.title, w.closestTitle = N.closestTitle, qe(p, w, N, m, y, i), k.mergePropertyMatch(m), k.mergeEnumValues(m);
          } else
            qe(p, h, N, m, y, i), k.mergePropertyMatch(m), k.mergeEnumValues(m);
        });
      }
    }
    const b = Qe(N.contains);
    if (b && (x.items.some((m) => {
      const p = new it(a);
      return qe(m, b, N, p, Zs.instance, i), !p.hasProblems();
    }) || k.problems.push({
      location: { offset: x.offset, length: x.length },
      severity: ce.Warning,
      message: N.errorMessage || me("requiredItemMissingWarning", "Array does not contain required item."),
      source: Se(N, n),
      schemaUri: Ee(N, n)
    })), wt(N.minItems) && x.items.length < N.minItems && k.problems.push({
      location: { offset: x.offset, length: x.length },
      severity: ce.Warning,
      message: me("minItemsWarning", "Array has too few items. Expected {0} or more.", N.minItems),
      source: Se(N, n),
      schemaUri: Ee(N, n)
    }), wt(N.maxItems) && x.items.length > N.maxItems && k.problems.push({
      location: { offset: x.offset, length: x.length },
      severity: ce.Warning,
      message: me("maxItemsWarning", "Array has too many items. Expected {0} or fewer.", N.maxItems),
      source: Se(N, n),
      schemaUri: Ee(N, n)
    }), N.uniqueItems === !0) {
      const h = Us(x);
      h.some((p, E) => E !== h.lastIndexOf(p)) && k.problems.push({
        location: { offset: x.offset, length: x.length },
        severity: ce.Warning,
        message: me("uniqueItemsWarning", "Array has duplicate items."),
        source: Se(N, n),
        schemaUri: Ee(N, n)
      });
    }
  }
  function d(x, N, k, y) {
    var b;
    const h = /* @__PURE__ */ Object.create(null), m = [], p = [...x.properties];
    for (; p.length > 0; ) {
      const L = p.pop(), C = L.keyNode.value;
      if (C === "<<" && L.valueNode)
        switch (L.valueNode.type) {
          case "object": {
            p.push(...L.valueNode.properties);
            break;
          }
          case "array": {
            L.valueNode.items.forEach((A) => {
              A && t5(A.properties) && p.push(...A.properties);
            });
            break;
          }
        }
      else
        h[C] = L.valueNode, m.push(C);
    }
    if (Array.isArray(N.required)) {
      for (const L of N.required)
        if (h[L] === void 0) {
          const C = x.parent && x.parent.type === "property" && x.parent.keyNode, A = C ? { offset: C.offset, length: C.length } : { offset: x.offset, length: 1 };
          k.problems.push({
            location: A,
            severity: ce.Warning,
            message: Ui(Xe.missingRequiredPropWarning, [L]),
            source: Se(N, n),
            schemaUri: Ee(N, n),
            problemArgs: [L],
            problemType: Xe.missingRequiredPropWarning
          });
        }
    }
    const E = (L) => {
      let C = m.indexOf(L);
      for (; C >= 0; )
        m.splice(C, 1), C = m.indexOf(L);
    };
    if (N.properties)
      for (const L of Object.keys(N.properties)) {
        E(L);
        const C = N.properties[L], A = h[L];
        if (A)
          if (Ir(C))
            if (C)
              k.propertiesMatches++, k.propertiesValueMatches++;
            else {
              const _ = A.parent;
              k.problems.push({
                location: {
                  offset: _.keyNode.offset,
                  length: _.keyNode.length
                },
                severity: ce.Warning,
                message: N.errorMessage || me("DisallowedExtraPropWarning", So, L),
                source: Se(N, n),
                schemaUri: Ee(N, n)
              });
            }
          else {
            C.url = (b = N.url) != null ? b : n.url;
            const _ = new it(a);
            qe(A, C, N, _, y, i), k.mergePropertyMatch(_), k.mergeEnumValues(_);
          }
      }
    if (N.patternProperties)
      for (const L of Object.keys(N.patternProperties)) {
        const C = Vd(L);
        for (const A of m.slice(0))
          if (C.test(A)) {
            E(A);
            const _ = h[A];
            if (_) {
              const O = N.patternProperties[L];
              if (Ir(O))
                if (O)
                  k.propertiesMatches++, k.propertiesValueMatches++;
                else {
                  const T = _.parent;
                  k.problems.push({
                    location: {
                      offset: T.keyNode.offset,
                      length: T.keyNode.length
                    },
                    severity: ce.Warning,
                    message: N.errorMessage || me("DisallowedExtraPropWarning", So, A),
                    source: Se(N, n),
                    schemaUri: Ee(N, n)
                  });
                }
              else {
                const T = new it(a);
                qe(_, O, N, T, y, i), k.mergePropertyMatch(T), k.mergeEnumValues(T);
              }
            }
          }
      }
    if (typeof N.additionalProperties == "object")
      for (const L of m) {
        const C = h[L];
        if (C) {
          const A = new it(a);
          qe(C, N.additionalProperties, N, A, y, i), k.mergePropertyMatch(A), k.mergeEnumValues(A);
        }
      }
    else if ((N.additionalProperties === !1 || N.type === "object" && N.additionalProperties === void 0 && i.disableAdditionalProperties === !0) && m.length > 0) {
      const L = N.properties && Object.entries(N.properties).filter(([C, A]) => !(h[C] || A && typeof A == "object" && (A.doNotSuggest || A.deprecationMessage))).map(([C]) => C);
      for (const C of m) {
        const A = h[C];
        if (A) {
          let _ = null;
          A.type !== "property" ? (_ = A.parent, _.type === "object" && (_ = _.properties[0])) : _ = A;
          const O = {
            location: {
              offset: _.keyNode.offset,
              length: _.keyNode.length
            },
            severity: ce.Warning,
            code: ct.PropertyExpected,
            message: N.errorMessage || me("DisallowedExtraPropWarning", So, C),
            source: Se(N, n),
            schemaUri: Ee(N, n)
          };
          L?.length && (O.data = { properties: L }), k.problems.push(O);
        }
      }
    }
    if (wt(N.maxProperties) && x.properties.length > N.maxProperties && k.problems.push({
      location: { offset: x.offset, length: x.length },
      severity: ce.Warning,
      message: me("MaxPropWarning", "Object has more properties than limit of {0}.", N.maxProperties),
      source: Se(N, n),
      schemaUri: Ee(N, n)
    }), wt(N.minProperties) && x.properties.length < N.minProperties && k.problems.push({
      location: { offset: x.offset, length: x.length },
      severity: ce.Warning,
      message: me("MinPropWarning", "Object has fewer properties than the required number of {0}", N.minProperties),
      source: Se(N, n),
      schemaUri: Ee(N, n)
    }), N.dependencies) {
      for (const L of Object.keys(N.dependencies))
        if (h[L]) {
          const A = N.dependencies[L];
          if (Array.isArray(A))
            for (const _ of A)
              h[_] ? k.propertiesValueMatches++ : k.problems.push({
                location: { offset: x.offset, length: x.length },
                severity: ce.Warning,
                message: me("RequiredDependentPropWarning", "Object is missing property {0} required by property {1}.", _, L),
                source: Se(N, n),
                schemaUri: Ee(N, n)
              });
          else {
            const _ = Qe(A);
            if (_) {
              const O = new it(a);
              qe(x, _, N, O, y, i), k.mergePropertyMatch(O), k.mergeEnumValues(O);
            }
          }
        }
    }
    const w = Qe(N.propertyNames);
    if (w)
      for (const L of x.properties) {
        const C = L.keyNode;
        C && qe(C, w, N, k, Zs.instance, i);
      }
  }
  function v(x, N, k, y) {
    const b = x.compareKubernetes(N.validationResult);
    return b > 0 ? N = {
      schema: k,
      validationResult: x,
      matchingSchemas: y
    } : b === 0 && (N.matchingSchemas.merge(y), N.validationResult.mergeEnumValues(x)), N;
  }
  function D(x, N, k, y, b, h) {
    if (!N && !k.hasProblems() && !y.validationResult.hasProblems())
      y.matchingSchemas.merge(h), y.validationResult.propertiesMatches += k.propertiesMatches, y.validationResult.propertiesValueMatches += k.propertiesValueMatches;
    else {
      const m = k.compareGeneric(y.validationResult);
      m > 0 || m === 0 && N && y.schema.type === "object" && x.type !== "null" && x.type !== y.schema.type ? y = {
        schema: b,
        validationResult: k,
        matchingSchemas: h
      } : (m === 0 || (x.value === null || x.type === "null") && x.length === 0) && S(y, h, k);
    }
    return y;
  }
  function S(x, N, k) {
    x.matchingSchemas.merge(N), x.validationResult.mergeEnumValues(k), x.validationResult.mergeWarningGeneric(k, [
      Xe.missingRequiredPropWarning,
      Xe.typeMismatchWarning,
      Xe.constWarning
    ]);
  }
}
function Se(e, t) {
  var n;
  if (e) {
    let r;
    if (e.title)
      r = e.title;
    else if (e.closestTitle)
      r = e.closestTitle;
    else if (t.closestTitle)
      r = t.closestTitle;
    else {
      const s = (n = e.url) != null ? n : t.url;
      if (s) {
        const i = yt.parse(s);
        i.scheme === "file" && (r = i.fsPath), r = i.toString();
      }
    }
    if (r)
      return `${ig}${r}`;
  }
  return Ha;
}
function Ee(e, t) {
  var n;
  const r = (n = e.url) != null ? n : t.url;
  return r ? [r] : [];
}
function Ui(e, t) {
  return me(e, b5[e], t.join(" | "));
}
function Wd(e, t, n, r) {
  return e ? n === null && t.length === 0 ? !0 : pa(n) && pa(r) && r.startsWith(n) : !1;
}
var L5 = 1e3, Kl = 0, Eo = /* @__PURE__ */ new Set();
function os(e, t, n, r) {
  if (e || (Kl = 0), !t)
    return null;
  if (Ve(t))
    return k5(t, e, n, r);
  if (Ae(t))
    return C5(t, e, n, r);
  if (Be(t))
    return F5(t, e, n, r);
  if (ae(t))
    return _5(t, e);
  if ($t(t) && !Eo.has(t) && Kl < L5) {
    Eo.add(t);
    const s = T5(t, e, n, r);
    return Eo.delete(t), s;
  } else
    return;
}
function k5(e, t, n, r) {
  let s;
  e.flow && !e.range ? s = M5(e) : s = e.range;
  const i = new A5(t, e, ...ug(s, r));
  for (const a of e.items)
    Ae(a) && i.properties.push(os(i, a, n, r));
  return i;
}
function C5(e, t, n, r) {
  const s = e.key, i = e.value, a = s.range[0];
  let o = s.range[1], l = s.range[2];
  i && (o = i.range[1], l = i.range[2]);
  const u = new E5(t, e, ...ug([a, o, l], r));
  if ($t(s)) {
    const f = new ga(t, s, ..._n(s.range));
    f.value = s.source, u.keyNode = f;
  } else
    u.keyNode = os(u, s, n, r);
  return u.valueNode = os(u, i, n, r), u;
}
function F5(e, t, n, r) {
  const s = new D5(t, e, ..._n(e.range));
  for (const i of e.items)
    if (De(i)) {
      const a = os(s, i, n, r);
      a && s.children.push(a);
    }
  return s;
}
function _5(e, t) {
  if (e.value === null)
    return new v5(t, e, ..._n(e.range));
  switch (typeof e.value) {
    case "string": {
      const n = new ga(t, e, ..._n(e.range));
      return n.value = e.value, n;
    }
    case "boolean":
      return new w5(t, e, e.value, e.source, ..._n(e.range));
    case "number": {
      const n = new S5(t, e, ..._n(e.range));
      return n.value = e.value, n.isInteger = Number.isInteger(n.value), n;
    }
    default: {
      const n = new ga(t, e, ..._n(e.range));
      return n.value = e.source, n;
    }
  }
}
function T5(e, t, n, r) {
  Kl++;
  const s = e.resolve(n);
  if (s)
    return os(t, s, n, r);
  {
    const i = new ga(t, e, ..._n(e.range));
    return i.value = e.source, i;
  }
}
function _n(e) {
  return [e[0], e[1] - e[0]];
}
function ug(e, t) {
  const n = t.linePos(e[0]), r = t.linePos(e[1]), s = [e[0], e[1] - e[0]];
  return n.line !== r.line && (t.lineStarts.length !== r.line || r.col === 1) && s[1]--, s;
}
function M5(e) {
  let t = Number.MAX_SAFE_INTEGER, n = 0;
  for (const r of e.items)
    Ae(r) && (De(r.key) && r.key.range && r.key.range[0] <= t && (t = r.key.range[0]), De(r.value) && r.value.range && r.value.range[2] >= n && (n = r.value.range[2]));
  return [t, n, n];
}
function O5(e, t) {
  let n;
  if (Me(e, (r, s, i) => {
    if (s === t)
      return n = i[i.length - 1], Me.BREAK;
  }), !us(n))
    return n;
}
function R5(e) {
  if (e.items.length > 1)
    return !1;
  const t = e.items[0];
  return ae(t.key) && ae(t.value) && t.key.value === "" && !t.value.value;
}
function P5(e, t) {
  for (const [n, r] of e.items.entries())
    if (t === r)
      return n;
}
function I5(e, t) {
  let n = !1;
  for (const r of e) {
    if (r.type === "document")
      Xl([], r, (s) => {
        var i;
        if (cg(s) && ((i = s.value) == null ? void 0 : i.type) === "comment") {
          if (r.offset <= t && s.value.source.length + s.value.offset >= t)
            return n = !0, Me.BREAK;
        } else if (s.type === "comment" && s.offset <= t && s.offset + s.source.length >= t)
          return n = !0, Me.BREAK;
      });
    else if (r.type === "comment" && r.offset <= t && r.source.length + r.offset >= t)
      return !0;
    if (n)
      break;
  }
  return n;
}
function cg(e) {
  return e.start !== void 0;
}
function Xl(e, t, n) {
  let r = n(t, e);
  if (typeof r == "symbol")
    return r;
  for (const i of ["key", "value"]) {
    const a = t[i];
    if (a && "items" in a) {
      for (let o = 0; o < a.items.length; ++o) {
        const l = Xl(Object.freeze(e.concat([[i, o]])), a.items[o], n);
        if (typeof l == "number")
          o = l - 1;
        else {
          if (l === Me.BREAK)
            return Me.BREAK;
          l === Me.REMOVE && (a.items.splice(o, 1), o -= 1);
        }
      }
      typeof r == "function" && i === "key" && (r = r(t, e));
    }
  }
  const s = t.sep;
  if (s)
    for (let i = 0; i < s.length; ++i) {
      const a = Xl(Object.freeze(e), s[i], n);
      if (typeof a == "number")
        i = a - 1;
      else {
        if (a === Me.BREAK)
          return Me.BREAK;
        a === Me.REMOVE && (s.items.splice(i, 1), i -= 1);
      }
    }
  return typeof r == "function" ? r(t, e) : r;
}
var fg = class hg extends N5 {
  constructor(t) {
    super(null, []), this.lineCounter = t;
  }
  /**
   * Create a deep copy of this document
   */
  clone() {
    const t = new hg(this.lineCounter);
    return t.isKubernetes = this.isKubernetes, t.disableAdditionalProperties = this.disableAdditionalProperties, t.uri = this.uri, t.currentDocIndex = this.currentDocIndex, t._lineComments = this.lineComments.slice(), t.internalDocument = this._internalDocument.clone(), t;
  }
  collectLineComments() {
    this._lineComments = [], this._internalDocument.commentBefore && this._internalDocument.commentBefore.split(`
`).forEach((n) => this._lineComments.push(`#${n}`)), Me(this.internalDocument, (t, n) => {
      n?.commentBefore && (n?.commentBefore.split(`
`)).forEach((s) => this._lineComments.push(`#${s}`)), n?.comment && this._lineComments.push(`#${n.comment}`);
    }), this._internalDocument.comment && this._lineComments.push(`#${this._internalDocument.comment}`);
  }
  /**
   * Updates the internal AST tree of the object
   * from the internal node. This is call whenever the
   * internalDocument is set but also can be called to
   * reflect any changes on the underlying document
   * without setting the internalDocument explicitly.
   */
  updateFromInternalDocument() {
    this.root = os(null, this._internalDocument.contents, this._internalDocument, this.lineCounter);
  }
  set internalDocument(t) {
    this._internalDocument = t, this.updateFromInternalDocument();
  }
  get internalDocument() {
    return this._internalDocument;
  }
  get lineComments() {
    return this._lineComments || this.collectLineComments(), this._lineComments;
  }
  set lineComments(t) {
    this._lineComments = t;
  }
  get errors() {
    return this.internalDocument.errors.map(Hd);
  }
  get warnings() {
    return this.internalDocument.warnings.map(Hd);
  }
  getNodeFromPosition(t, n, r) {
    const s = n.getPosition(t), i = n.getLineContent(s.line);
    if (i.trim().length === 0)
      return [this.findClosestNode(t, n, r), !0];
    const o = i.substring(s.character).match(/^([ ]+)\n?$/), l = !!o, u = o?.[1].length;
    let f;
    return Me(this.internalDocument, (c, d) => {
      if (!d)
        return;
      const v = d.range;
      if (!v)
        return;
      const D = () => l && t + u === v[2] && ae(d) && d.value === null;
      if (v[0] <= t && v[1] >= t || D())
        f = d;
      else
        return Me.SKIP;
    }), [f, !1];
  }
  findClosestNode(t, n, r) {
    let s = this.internalDocument.range[2], i = this.internalDocument.range[0], a;
    Me(this.internalDocument, (f, c) => {
      if (!c)
        return;
      const d = c.range;
      if (!d)
        return;
      const v = d[1] - t;
      i <= d[0] && v <= 0 && Math.abs(v) <= s && (s = Math.abs(v), i = d[0], a = c);
    });
    const o = n.getPosition(t), l = n.getLineContent(o.line), u = Z8(l, o.character);
    return ae(a) && a.value === null || u === o.character && (a = this.getProperParentByIndentation(u, a, n, "", r)), a;
  }
  getProperParentByIndentation(t, n, r, s, i, a) {
    if (!n)
      return this.internalDocument.contents;
    if (i = i || 2, De(n) && n.range) {
      const o = r.getPosition(n.range[0]), l = r.getLineContent(o.line);
      if (s = s === "" ? l.trim() : s, s.startsWith("-") && t === i && s === l.trim() && (o.character += t), o.character > t && o.character > 0) {
        const u = this.getParent(n);
        if (u)
          return this.getProperParentByIndentation(t, u, r, s, i, a);
      } else if (o.character < t) {
        const u = this.getParent(n);
        if (Ae(u) && De(u.value))
          return u.value;
        if (Ae(a) && De(a.value))
          return a.value;
      } else
        return n;
    } else if (Ae(n)) {
      a = n;
      const o = this.getParent(n);
      return this.getProperParentByIndentation(t, o, r, s, i, a);
    }
    return n;
  }
  getParent(t) {
    return O5(this.internalDocument, t);
  }
}, dg = class {
  constructor(e, t) {
    this.documents = e, this.tokens = t, this.errors = [], this.warnings = [];
  }
}, $5 = class {
  constructor() {
    this.cache = /* @__PURE__ */ new Map();
  }
  /**
   * Get cached YAMLDocument
   * @param document TextDocument to parse
   * @param parserOptions YAML parserOptions
   * @param addRootObject if true and document is empty add empty object {} to force schema usage
   * @returns the YAMLDocument
   */
  getYamlDocument(e, t, n = !1) {
    return this.ensureCache(e, t ?? ya, n), this.cache.get(e.uri).document;
  }
  /**
   * For test purpose only!
   */
  clear() {
    this.cache.clear();
  }
  ensureCache(e, t, n) {
    const r = e.uri;
    this.cache.has(r) || this.cache.set(r, { version: -1, document: new dg([], []), parserOptions: ya });
    const s = this.cache.get(r);
    if (s.version !== e.version || t.customTags && !sg(s.parserOptions.customTags, t.customTags)) {
      let i = e.getText();
      n && !/\S/.test(i) && (i = `{${i}}`);
      const a = U5(i, t, e);
      s.document = a, s.version = e.version, s.parserOptions = t;
    }
  }
}, It = new $5();
function Hd(e) {
  return {
    message: e.message,
    location: {
      start: e.pos[0],
      end: e.pos[1],
      toLineEnd: !0
    },
    severity: 1,
    code: ct.Undefined
  };
}
var B5 = class {
  constructor(e, t) {
    this.tag = e, this.type = t;
  }
  get collection() {
    if (this.type === "mapping")
      return "map";
    if (this.type === "sequence")
      return "seq";
  }
  resolve(e) {
    if (Ve(e) && this.type === "mapping" || Be(e) && this.type === "sequence" || typeof e == "string" && this.type === "scalar")
      return e;
  }
}, V5 = class {
  constructor() {
    this.tag = "!include", this.type = "scalar";
  }
  resolve(e, t) {
    if (e && e.length > 0 && e.trim())
      return e;
    t("!include without value");
  }
};
function j5(e) {
  const t = [], n = rg(e);
  for (const r of n) {
    const s = r.split(" "), i = s[0], a = s[1] && s[1].toLowerCase() || "scalar";
    t.push(new B5(i, a));
  }
  return t.push(new V5()), t;
}
var cr = class {
  constructor(e) {
    this.doc = e;
  }
  getLineCount() {
    return this.doc.lineCount;
  }
  getLineLength(e) {
    const t = this.doc.getLineOffsets();
    return e >= t.length ? this.doc.getText().length : e < 0 ? 0 : (e + 1 < t.length ? t[e + 1] : this.doc.getText().length) - t[e];
  }
  getLineContent(e) {
    const t = this.doc.getLineOffsets();
    if (e >= t.length)
      return this.doc.getText();
    if (e < 0)
      return "";
    const n = e + 1 < t.length ? t[e + 1] : this.doc.getText().length;
    return this.doc.getText().substring(t[e], n);
  }
  getLineCharCode(e, t) {
    return this.doc.getText(ie.create(e - 1, t, e - 1, t + 1)).charCodeAt(0);
  }
  getText(e) {
    return this.doc.getText(e);
  }
  getPosition(e) {
    return this.doc.positionAt(e);
  }
}, ya = {
  customTags: [],
  yamlVersion: "1.2"
};
function U5(e, t = ya, n) {
  var r;
  const s = {
    strict: !1,
    customTags: j5(t.customTags),
    version: (r = t.yamlVersion) != null ? r : ya.yamlVersion,
    keepSourceTokens: !0
  }, i = new sm(s), a = new fm();
  let o = !1;
  if (n) {
    const v = new cr(n), D = v.getPosition(e.length);
    o = v.getLineContent(D.line).trim().length === 0;
  }
  const u = (o ? new kl() : new kl(a.addNewLine)).parse(e), f = Array.from(u), c = i.compose(f, !0, e.length), d = Array.from(c, (v) => q5(v, a));
  return new dg(d, f);
}
function q5(e, t) {
  const n = new fg(t);
  return n.internalDocument = e, n;
}
function W5(e) {
  if (e instanceof fg) {
    const t = e.lineComments.find((n) => Zl(n));
    if (t != null) {
      const n = t.match(/\$schema=\S+/g);
      if (n !== null && n.length >= 1)
        return n.length >= 2 && console.log("Several $schema attributes have been found on the yaml-language-server modeline. The first one will be picked."), n[0].substring(8);
    }
  }
}
function Zl(e) {
  const t = e.match(/^#\s+yaml-language-server\s*:/g);
  return t !== null && t.length === 1;
}
var H5 = class {
  // eslint-disable-next-line @typescript-eslint/class-methods-use-this
  compile() {
    return () => !0;
  }
}, Y5 = new H5(), Si = ps(), z5 = void 0, Yd = Y5.compile(z5), zd;
(function(e) {
  e[e.delete = 0] = "delete", e[e.add = 1] = "add", e[e.deleteAll = 2] = "deleteAll";
})(zd || (zd = {}));
var G5 = class {
  constructor(e) {
    try {
      this.patternRegExp = new RegExp(X8(e) + "$");
    } catch {
      this.patternRegExp = null;
    }
    this.schemas = [];
  }
  addSchema(e) {
    this.schemas.push(e);
  }
  matchesPattern(e) {
    return this.patternRegExp && this.patternRegExp.test(e);
  }
  getSchemas() {
    return this.schemas;
  }
}, J5 = class extends J8 {
  constructor(e, t, n) {
    super(e, t, n), this.schemaUriToNameAndDescription = /* @__PURE__ */ new Map(), this.customSchemaProvider = void 0, this.requestService = e, this.schemaPriorityMapping = /* @__PURE__ */ new Map();
  }
  registerCustomSchemaProvider(e) {
    this.customSchemaProvider = e;
  }
  getAllSchemas() {
    const e = [], t = /* @__PURE__ */ new Set();
    for (const n of this.filePatternAssociations) {
      const r = n.uris[0];
      if (t.has(r))
        continue;
      t.add(r);
      const s = {
        uri: r,
        fromStore: !1,
        usedForCurrentFile: !1
      };
      if (this.schemaUriToNameAndDescription.has(r)) {
        const { name: i, description: a, versions: o } = this.schemaUriToNameAndDescription.get(r);
        s.name = i, s.description = a, s.fromStore = !0, s.versions = o;
      }
      e.push(s);
    }
    return e;
  }
  async resolveSchemaContent(e, t, n) {
    const r = e.errors.slice(0);
    let s = e.schema;
    const i = this.contextService;
    if (!Yd(s)) {
      const f = [];
      for (const c of Yd.errors)
        f.push(`${c.instancePath} : ${c.message}`);
      r.push(`Schema '${eg(e.schema, t)}' is not valid:
${f.join(`
`)}`);
    }
    const a = (f, c) => {
      if (!c)
        return f;
      let d = f;
      return c[0] === "/" && (c = c.substr(1)), c.split("/").some((v) => (d = d[v], !d)), d;
    }, o = (f, c, d, v) => {
      const D = a(c, v);
      if (D)
        for (const S in D)
          Object.prototype.hasOwnProperty.call(D, S) && !Object.prototype.hasOwnProperty.call(f, S) && (f[S] = D[S]);
      else
        r.push(Si("json.schema.invalidref", "$ref '{0}' in '{1}' can not be resolved.", v, d));
    }, l = (f, c, d, v, D) => {
      i && !/^\w+:\/\/.*/.test(c) && (c = i.resolveRelativePath(c, v)), c = this.normalizeId(c);
      const S = this.getOrAddSchemaHandle(c);
      return S.getUnresolvedSchema().then((x) => {
        if (D[c] = !0, x.errors.length) {
          const N = d ? c + "#" + d : c;
          r.push(Si("json.schema.problemloadingref", "Problems loading reference '{0}': {1}", N, x.errors[0]));
        }
        return o(f, x.schema, c, d), f.url = c, u(f, x.schema, c, S.dependencies);
      });
    }, u = async (f, c, d, v) => {
      if (!f || typeof f != "object")
        return null;
      const D = [f], S = /* @__PURE__ */ new Set(), x = [], N = (...h) => {
        for (const m of h)
          typeof m == "object" && D.push(m);
      }, k = (...h) => {
        for (const m of h)
          if (typeof m == "object")
            for (const p in m) {
              const E = m[p];
              typeof E == "object" && D.push(E);
            }
      }, y = (...h) => {
        for (const m of h)
          if (Array.isArray(m))
            for (const p of m)
              typeof p == "object" && D.push(p);
      }, b = (h) => {
        const m = /* @__PURE__ */ new Set();
        for (; h.$ref; ) {
          const p = decodeURIComponent(h.$ref), E = p.split("#", 2);
          if (h._$ref = h.$ref, delete h.$ref, E[0].length > 0) {
            x.push(l(h, E[0], E[1], d, v));
            return;
          } else
            m.has(p) || (o(h, c, d, E[1]), m.add(p));
        }
        N(h.items, h.additionalItems, h.additionalProperties, h.not, h.contains, h.propertyNames, h.if, h.then, h.else), k(h.definitions, h.properties, h.patternProperties, h.dependencies), y(h.anyOf, h.allOf, h.oneOf, h.items, h.schemaSequence);
      };
      if (d.indexOf("#") > 0) {
        const h = d.split("#", 2);
        if (h[0].length > 0 && h[1].length > 0) {
          const m = {};
          await l(m, h[0], h[1], d, v);
          for (const p in s)
            p !== "required" && Object.prototype.hasOwnProperty.call(s, p) && !Object.prototype.hasOwnProperty.call(m, p) && (m[p] = s[p]);
          s = m;
        }
      }
      for (; D.length; ) {
        const h = D.pop();
        S.has(h) || (S.add(h), b(h));
      }
      return Promise.all(x);
    };
    return await u(s, s, t, n), new js(s, r);
  }
  getSchemaForResource(e, t) {
    const n = () => {
      let a = W5(t);
      if (a !== void 0) {
        if (!a.startsWith("file:") && !a.startsWith("http")) {
          let o = "";
          if (a.indexOf("#") > 0) {
            const l = a.split("#", 2);
            a = l[0], o = l[1];
          }
          if (nr.isAbsolute(a))
            a = yt.file(a).toString();
          else {
            const l = yt.parse(e);
            a = yt.file(nr.resolve(nr.parse(l.fsPath).dir, a)).toString();
          }
          o.length > 0 && (a += "#" + o);
        }
        return a;
      }
    }, r = (a) => {
      const o = super.createCombinedSchema(e, a);
      return o.getResolvedSchema().then((l) => (l.schema && typeof l.schema == "object" && (l.schema.url = o.url), l.schema && l.schema.schemaSequence && l.schema.schemaSequence[t.currentDocIndex] ? new js(l.schema.schemaSequence[t.currentDocIndex]) : l));
    }, s = () => {
      const a = /* @__PURE__ */ Object.create(null), o = [];
      for (const l of this.filePatternAssociations)
        if (l.matchesPattern(e))
          for (const u of l.getURIs())
            a[u] || (o.push(u), a[u] = !0);
      if (o.length > 0) {
        const l = this.highestPrioritySchemas(o);
        return r(l);
      }
      return Promise.resolve(null);
    }, i = n();
    return i ? r([i]) : this.customSchemaProvider ? this.customSchemaProvider(e).then((a) => Array.isArray(a) ? a.length === 0 ? s() : Promise.all(a.map((o) => this.resolveCustomSchema(o, t))).then((o) => ({
      errors: [],
      schema: {
        allOf: o.map((l) => l.schema)
      }
    }), () => s()) : a ? this.resolveCustomSchema(a, t) : s()).then((a) => a, () => s()) : s();
  }
  // Set the priority of a schema in the schema service
  addSchemaPriority(e, t) {
    let n = this.schemaPriorityMapping.get(e);
    n ? (n = n.add(t), this.schemaPriorityMapping.set(e, n)) : this.schemaPriorityMapping.set(e, (/* @__PURE__ */ new Set()).add(t));
  }
  /**
   * Search through all the schemas and find the ones with the highest priority
   */
  highestPrioritySchemas(e) {
    let t = 0;
    const n = /* @__PURE__ */ new Map();
    return e.forEach((r) => {
      (this.schemaPriorityMapping.get(r) || [0]).forEach((i) => {
        i > t && (t = i);
        let a = n.get(i);
        a ? (a = a.concat(r), n.set(i, a)) : n.set(i, [r]);
      });
    }), n.get(t) || [];
  }
  async resolveCustomSchema(e, t) {
    const n = await this.loadSchema(e), r = await this.resolveSchemaContent(n, e, []);
    return r.schema && typeof r.schema == "object" && (r.schema.url = e), r.schema && r.schema.schemaSequence && r.schema.schemaSequence[t.currentDocIndex] ? new js(r.schema.schemaSequence[t.currentDocIndex], r.errors) : r;
  }
  /**
   * Save a schema with schema ID and schema content.
   * Overrides previous schemas set for that schema ID.
   */
  async saveSchema(e, t) {
    const n = this.normalizeId(e);
    return this.getOrAddSchemaHandle(n, t), this.schemaPriorityMapping.set(n, (/* @__PURE__ */ new Set()).add(eu.Settings)), Promise.resolve(void 0);
  }
  /**
   * Delete schemas on specific path
   */
  async deleteSchemas(e) {
    return e.schemas.forEach((t) => {
      this.deleteSchema(t);
    }), Promise.resolve(void 0);
  }
  /**
   * Delete a schema with schema ID.
   */
  async deleteSchema(e) {
    const t = this.normalizeId(e);
    return this.schemasById[t] && delete this.schemasById[t], this.schemaPriorityMapping.delete(t), Promise.resolve(void 0);
  }
  /**
   * Add content to a specified schema at a specified path
   */
  async addContent(e) {
    const t = await this.getResolvedSchema(e.schema);
    if (t) {
      const n = this.resolveJSONSchemaToSection(t.schema, e.path);
      typeof n == "object" && (n[e.key] = e.content), await this.saveSchema(e.schema, t.schema);
    }
  }
  /**
   * Delete content in a specified schema at a specified path
   */
  async deleteContent(e) {
    const t = await this.getResolvedSchema(e.schema);
    if (t) {
      const n = this.resolveJSONSchemaToSection(t.schema, e.path);
      typeof n == "object" && delete n[e.key], await this.saveSchema(e.schema, t.schema);
    }
  }
  /**
   * Take a JSON Schema and the path that you would like to get to
   * @returns the JSON Schema resolved at that specific path
   */
  resolveJSONSchemaToSection(e, t) {
    const n = t.split("/");
    let r = e;
    for (const s of n)
      s !== "" && (this.resolveNext(r, s), r = r[s]);
    return r;
  }
  /**
   * Resolve the next Object if they have compatible types
   * @param object a location in the JSON Schema
   * @param token the next token that you want to search for
   */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  resolveNext(e, t) {
    if (Array.isArray(e) && isNaN(t))
      throw new Error("Expected a number after the array object");
    if (typeof e == "object" && typeof t != "string")
      throw new Error("Expected a string after the object");
  }
  /**
   * Everything below here is needed because we're importing from vscode-json-languageservice umd and we need
   * to provide a wrapper around the javascript methods we are calling since they have no type
   */
  normalizeId(e) {
    try {
      return yt.parse(e).toString();
    } catch {
      return e;
    }
  }
  /*
   * Everything below here is needed because we're importing from vscode-json-languageservice umd and we need
   * to provide a wrapper around the javascript methods we are calling since they have no type
   */
  getOrAddSchemaHandle(e, t) {
    return super.getOrAddSchemaHandle(e, t);
  }
  loadSchema(e) {
    const t = this.requestService;
    return super.loadSchema(e).then((n) => {
      if (n.errors && n.schema === void 0)
        return t(e).then(
          (r) => {
            if (!r) {
              const s = Si("json.schema.nocontent", "Unable to load schema from '{0}': No content. {1}", Gd(e), n.errors);
              return new Rt({}, [s]);
            }
            try {
              const s = M2(r);
              return new Rt(s, []);
            } catch (s) {
              const i = Si("json.schema.invalidFormat", "Unable to parse content from '{0}': {1}.", Gd(e), s);
              return new Rt({}, [i]);
            }
          },
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (r) => {
            let s = r.toString();
            const i = r.toString().split("Error: ");
            return i.length > 1 && (s = i[1]), new Rt({}, [s]);
          }
        );
      if (n.uri = e, this.schemaUriToNameAndDescription.has(e)) {
        const { name: r, description: s, versions: i } = this.schemaUriToNameAndDescription.get(e);
        n.schema.title = r ?? n.schema.title, n.schema.description = s ?? n.schema.description, n.schema.versions = i ?? n.schema.versions;
      }
      return n;
    });
  }
  registerExternalSchema(e, t, n, r, s, i) {
    return (r || s) && this.schemaUriToNameAndDescription.set(e, { name: r, description: s, versions: i }), super.registerExternalSchema(e, t, n);
  }
  clearExternalSchemas() {
    super.clearExternalSchemas();
  }
  setSchemaContributions(e) {
    super.setSchemaContributions(e);
  }
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  getRegisteredSchemaIds(e) {
    return super.getRegisteredSchemaIds(e);
  }
  getResolvedSchema(e) {
    return super.getResolvedSchema(e);
  }
  onResourceChange(e) {
    return super.onResourceChange(e);
  }
};
function Gd(e) {
  try {
    const t = yt.parse(e);
    if (t.scheme === "file")
      return t.fsPath;
  } catch {
  }
  return e;
}
var Q5 = class {
  constructor(e, t) {
    this.telemetry = t, this.jsonDocumentSymbols = new c5(e), this.jsonDocumentSymbols.getKeyLabel = (n) => {
      const r = n.keyNode.internalNode;
      let s = "";
      return Ve(r) ? s = "{}" : Be(r) ? s = "[]" : s = r.source, s;
    };
  }
  findDocumentSymbols(e, t = { resultLimit: Number.MAX_VALUE }) {
    var n;
    let r = [];
    try {
      const s = It.getYamlDocument(e);
      if (!s || s.documents.length === 0)
        return null;
      for (const i of s.documents)
        i.root && (r = r.concat(this.jsonDocumentSymbols.findDocumentSymbols(e, i, t)));
    } catch (s) {
      (n = this.telemetry) == null || n.sendError("yaml.documentSymbols.error", s);
    }
    return r;
  }
  findHierarchicalDocumentSymbols(e, t = { resultLimit: Number.MAX_VALUE }) {
    var n;
    let r = [];
    try {
      const s = It.getYamlDocument(e);
      if (!s || s.documents.length === 0)
        return null;
      for (const i of s.documents)
        i.root && (r = r.concat(this.jsonDocumentSymbols.findDocumentSymbols2(e, i, t)));
    } catch (s) {
      (n = this.telemetry) == null || n.sendError("yaml.hierarchicalDocumentSymbols.error", s);
    }
    return r;
  }
};
function mg(e, t) {
  for (const n of e)
    n.isKubernetes = t;
}
var K5 = class {
  constructor(e, t) {
    this.telemetry = t, this.shouldHover = !0, this.schemaService = e;
  }
  configure(e) {
    e && (this.shouldHover = e.hover, this.indentation = e.indentation);
  }
  doHover(e, t, n = !1) {
    var r;
    try {
      if (!this.shouldHover || !e)
        return Promise.resolve(void 0);
      const s = It.getYamlDocument(e), i = e.offsetAt(t), a = Wa(i, s);
      if (a === null)
        return Promise.resolve(void 0);
      mg(s.documents, n);
      const o = s.documents.indexOf(a);
      return a.currentDocIndex = o, this.getHover(e, t, a);
    } catch (s) {
      (r = this.telemetry) == null || r.sendError("yaml.hover.error", s);
    }
  }
  // method copied from https://github.com/microsoft/vscode-json-languageservice/blob/2ea5ad3d2ffbbe40dea11cfe764a502becf113ce/src/services/jsonHover.ts#L23
  getHover(e, t, n) {
    const r = e.offsetAt(t);
    let s = n.getNodeFromOffset(r);
    if (!s || (s.type === "object" || s.type === "array") && r > s.offset + 1 && r < s.offset + s.length - 1)
      return Promise.resolve(null);
    const i = s;
    if (s.type === "string") {
      const u = s.parent;
      if (u && u.type === "property" && u.keyNode === s && (s = u.valueNode, !s))
        return Promise.resolve(null);
    }
    const a = ie.create(e.positionAt(i.offset), e.positionAt(i.offset + i.length)), o = (u) => ({
      contents: {
        kind: hn.Markdown,
        value: u
      },
      range: a
    }), l = (u) => u.replace(/\s\|\|\s*$/, "");
    return this.schemaService.getSchemaForResource(e.uri, n).then((u) => {
      if (u && s && !u.errors.length) {
        const f = n.getMatchingSchemas(u.schema, s.offset);
        let c, d, v = [];
        const D = [], S = [];
        f.every((N) => ((N.node === s || s.type === "property" && s.valueNode === N.node) && !N.inverted && N.schema && (c = c || N.schema.title || N.schema.closestTitle, d = d || N.schema.markdownDescription || this.toMarkdown(N.schema.description), N.schema.enum && (N.schema.markdownEnumDescriptions ? v = N.schema.markdownEnumDescriptions : N.schema.enumDescriptions ? v = N.schema.enumDescriptions.map(this.toMarkdown, this) : v = [], N.schema.enum.forEach((k, y) => {
          typeof k != "string" && (k = JSON.stringify(k)), S.some((b) => b.value === k) || S.push({
            value: k,
            description: v[y]
          });
        })), N.schema.anyOf && Z5(s, f, N.schema) && (c = "", d = N.schema.description ? N.schema.description + `
` : "", N.schema.anyOf.forEach((k, y) => {
          c += k.title || N.schema.closestTitle || "", d += k.markdownDescription || this.toMarkdown(k.description) || "", y !== N.schema.anyOf.length - 1 && (c += " || ", d += " || ");
        }), c = l(c), d = l(d)), N.schema.examples && N.schema.examples.forEach((k) => {
          D.push(O2(k, null, 2));
        })), !0));
        let x = "";
        return c && (x = "#### " + this.toMarkdown(c)), d && (x = Ei(x), x += d), S.length !== 0 && (x = Ei(x), x += `Allowed Values:

`, S.forEach((N) => {
          N.description ? x += `* \`${Jd(N.value)}\`: ${N.description}
` : x += `* \`${Jd(N.value)}\`
`;
        })), D.length !== 0 && D.forEach((N) => {
          x = Ei(x), x += `Example:

`, x += `\`\`\`yaml
${N}\`\`\`
`;
        }), x.length > 0 && u.schema.url && (x = Ei(x), x += `Source: [${X5(u.schema)}](${u.schema.url})`), o(x);
      }
      return null;
    });
  }
  // copied from https://github.com/microsoft/vscode-json-languageservice/blob/2ea5ad3d2ffbbe40dea11cfe764a502becf113ce/src/services/jsonHover.ts#L112
  toMarkdown(e) {
    if (e) {
      let t = e.replace(/([^\n\r])(\r?\n)([^\n\r])/gm, `$1

$3`);
      if (t = t.replace(/[\\`*_{}[\]()#+\-.!]/g, "\\$&"), this.indentation !== void 0) {
        const n = new RegExp(` {${this.indentation.length}}`, "g");
        t = t.replace(n, "&emsp;");
      }
      return t;
    }
  }
};
function Ei(e) {
  return e.length === 0 ? e : (e.endsWith(`
`) || (e += `
`), e + `
`);
}
function X5(e) {
  let t = "JSON Schema";
  const n = e.url;
  if (n) {
    const r = yt.parse(n);
    t = nr.basename(r.fsPath);
  } else e.title && (t = e.title);
  return t;
}
function Jd(e) {
  return e.indexOf("`") !== -1 ? "`` " + e + " ``" : e;
}
function Z5(e, t, n) {
  let r = 0;
  for (const s of t)
    e === s.node && s.schema !== n && n.anyOf.forEach((i) => {
      s.schema.title === i.title && s.schema.description === i.description && s.schema.properties === i.properties && r++;
    });
  return r === n.anyOf.length;
}
var e6 = class {
  validate(e, t) {
    const n = [], r = /* @__PURE__ */ new Set(), s = /* @__PURE__ */ new Set(), i = /* @__PURE__ */ new Map();
    Me(t.internalDocument, (a, o, l) => {
      De(o) && ((Pe(o) || ae(o)) && o.anchor && (r.add(o), i.set(o, l[l.length - 1])), $t(o) && s.add(o.resolve(t.internalDocument)));
    });
    for (const a of r)
      if (!s.has(a)) {
        const o = this.getAnchorNode(i.get(a), a);
        if (o) {
          const l = ie.create(e.positionAt(o.offset), e.positionAt(o.offset + o.source.length)), u = bt.create(l, `Unused anchor "${o.source}"`, ce.Hint, 0);
          u.tags = [ol.Unnecessary], n.push(u);
        }
      }
    return n;
  }
  getAnchorNode(e, t) {
    if (e && e.srcToken) {
      const n = e.srcToken;
      if (cg(n))
        return Qd(n);
      if (N2(n))
        for (const r of n.items) {
          if (t.srcToken !== r.value)
            continue;
          const s = Qd(r);
          if (s)
            return s;
        }
    }
  }
};
function Qd(e) {
  for (const t of e.start)
    if (t.type === "anchor")
      return t;
  if (e.sep && Array.isArray(e.sep)) {
    for (const t of e.sep)
      if (t.type === "anchor")
        return t;
  }
}
var t6 = class {
  constructor(e) {
    this.forbidMapping = e.flowMapping === "forbid", this.forbidSequence = e.flowSequence === "forbid";
  }
  validate(e, t) {
    const n = [];
    return Me(t.internalDocument, (r, s) => {
      var i, a;
      this.forbidMapping && Ve(s) && ((i = s.srcToken) == null ? void 0 : i.type) === "flow-collection" && n.push(bt.create(this.getRangeOf(e, s.srcToken), "Flow style mapping is forbidden", ce.Error, "flowMap")), this.forbidSequence && Be(s) && ((a = s.srcToken) == null ? void 0 : a.type) === "flow-collection" && n.push(bt.create(this.getRangeOf(e, s.srcToken), "Flow style sequence is forbidden", ce.Error, "flowSeq"));
    }), n;
  }
  getRangeOf(e, t) {
    return ie.create(e.positionAt(t.start.offset), e.positionAt(t.end.pop().offset));
  }
}, n6 = class {
  validate(e, t) {
    const n = [];
    return Me(t.internalDocument, (r, s) => {
      if (Ve(s)) {
        for (let i = 1; i < s.items.length; i++)
          if (s6(s.items[i - 1], s.items[i]) > 0) {
            const a = r6(e, s.items[i - 1]);
            n.push(bt.create(a, `Wrong ordering of key "${s.items[i - 1].key}" in mapping`, ce.Error, "mapKeyOrder"));
          }
      }
    }), n;
  }
};
function r6(e, t) {
  var n, r, s, i, a, o, l, u, f, c, d;
  const v = (o = (s = (n = t?.srcToken.start[0]) == null ? void 0 : n.offset) != null ? s : (r = t?.srcToken) == null ? void 0 : r.key.offset) != null ? o : (a = (i = t?.srcToken) == null ? void 0 : i.sep[0]) == null ? void 0 : a.offset, D = ((l = t?.srcToken) == null ? void 0 : l.value.offset) || ((f = (u = t?.srcToken) == null ? void 0 : u.sep[0]) == null ? void 0 : f.offset) || ((c = t?.srcToken) == null ? void 0 : c.key.offset) || ((d = t?.srcToken.start[t.srcToken.start.length - 1]) == null ? void 0 : d.offset);
  return ie.create(e.positionAt(v), e.positionAt(D));
}
function s6(e, t) {
  const n = String(t.key);
  return String(e.key).localeCompare(n);
}
var i6 = (e, t) => {
  const n = t.positionAt(e.location.start), r = {
    start: n,
    end: e.location.toLineEnd ? Ye.create(n.line, new cr(t).getLineLength(n.line)) : t.positionAt(e.location.end)
  };
  return bt.create(r, e.message, e.severity, e.code, Ha);
}, a6 = class {
  constructor(e, t) {
    this.telemetry = t, this.validators = [], this.MATCHES_MULTIPLE = "Matches multiple schemas when only one must validate.", this.validationEnabled = !0, this.jsonValidation = new s5(e, Promise);
  }
  configure(e) {
    this.validators = [], e && (this.validationEnabled = e.validate, this.customTags = e.customTags, this.disableAdditionalProperties = e.disableAdditionalProperties, this.yamlVersion = e.yamlVersion, (e.flowMapping === "forbid" || e.flowSequence === "forbid") && this.validators.push(new t6(e)), e.keyOrdering && this.validators.push(new n6())), this.validators.push(new e6());
  }
  async doValidation(e, t = !1) {
    var n;
    if (!this.validationEnabled)
      return Promise.resolve([]);
    const r = [];
    try {
      const o = It.getYamlDocument(e, { customTags: this.customTags, yamlVersion: this.yamlVersion }, !0);
      let l = 0;
      for (const u of o.documents) {
        u.isKubernetes = t, u.currentDocIndex = l, u.disableAdditionalProperties = this.disableAdditionalProperties, u.uri = e.uri;
        const f = await this.jsonValidation.doValidation(e, u), c = u;
        c.errors.length > 0 && r.push(...c.errors), c.warnings.length > 0 && r.push(...c.warnings), r.push(...f), r.push(...this.runAdditionalValidators(e, u)), l++;
      }
    } catch (o) {
      (n = this.telemetry) == null || n.sendError("yaml.validation.error", o);
    }
    let s;
    const i = /* @__PURE__ */ new Set(), a = [];
    for (let o of r) {
      if (t && o.message === this.MATCHES_MULTIPLE)
        continue;
      if (Object.prototype.hasOwnProperty.call(o, "location") && (o = i6(o, e)), o.source || (o.source = Ha), s && s.message === o.message && s.range.end.line === o.range.start.line && Math.abs(s.range.end.character - o.range.end.character) >= 1) {
        s.range.end = o.range.end;
        continue;
      } else
        s = o;
      const l = o.range.start.line + " " + o.range.start.character + " " + o.message;
      i.has(l) || (a.push(o), i.add(l));
    }
    return a;
  }
  runAdditionalValidators(e, t) {
    const n = [];
    for (const r of this.validators)
      n.push(...r.validate(e, t));
    return n;
  }
}, o6 = class {
  constructor() {
    this.formatterEnabled = !0;
  }
  configure(e) {
    e && (this.formatterEnabled = e.format);
  }
  async format(e, t = {}) {
    if (!this.formatterEnabled)
      return [];
    try {
      const n = e.getText(), r = {
        parser: "yaml",
        plugins: [pD],
        // --- FormattingOptions ---
        tabWidth: t.tabWidth || t.tabSize,
        // --- CustomFormatterOptions ---
        singleQuote: t.singleQuote,
        bracketSpacing: t.bracketSpacing,
        // 'preserve' is the default for Options.proseWrap. See also server.ts
        proseWrap: t.proseWrap === "always" ? "always" : t.proseWrap === "never" ? "never" : "preserve",
        printWidth: t.printWidth
      }, s = await Ku(n, r);
      return [_e.replace(ie.create(Ye.create(0, 0), e.positionAt(n.length)), s)];
    } catch {
      return [];
    }
  }
}, l6 = class {
  constructor(e) {
    this.telemetry = e;
  }
  findLinks(e) {
    var t;
    try {
      const n = It.getYamlDocument(e), r = [];
      for (const s of n.documents)
        r.push(f5(e, s));
      return Promise.all(r).then((s) => [].concat(...s));
    } catch (n) {
      (t = this.telemetry) == null || t.sendError("yaml.documentLink.error", n);
    }
  }
};
function u6(e, t) {
  if (!e)
    return;
  const n = [], r = It.getYamlDocument(e);
  for (const i of r.documents)
    r.documents.length > 1 && n.push(Ai(e, i.root)), i.visit((a) => {
      var o;
      if (a.type === "object" && ((o = a.parent) == null ? void 0 : o.type) === "array" && n.push(Ai(e, a)), a.type === "property" && a.valueNode)
        switch (a.valueNode.type) {
          case "array":
          case "object":
            n.push(Ai(e, a));
            break;
          case "string": {
            const l = e.positionAt(a.offset), u = e.positionAt(a.valueNode.offset + a.valueNode.length);
            l.line !== u.line && n.push(Ai(e, a));
            break;
          }
          default:
            return !0;
        }
      return !0;
    });
  const s = t && t.rangeLimit;
  return typeof s != "number" || n.length <= s ? n : (t && t.onRangeLimitExceeded && t.onRangeLimitExceeded(e.uri), n.slice(0, t.rangeLimit));
}
function Ai(e, t) {
  const n = e.positionAt(t.offset);
  let r = e.positionAt(t.offset + t.length);
  const s = e.getText(ie.create(n, r)), i = s.length - s.trimRight().length;
  return i > 0 && (r = e.positionAt(t.offset + t.length - i)), il.create(n.line, r.line, n.character, r.character);
}
var ba;
(function(e) {
  e.JUMP_TO_SCHEMA = "jumpToSchema";
})(ba || (ba = {}));
var c6 = class {
  constructor(e) {
    this.indentation = e;
  }
  write(e) {
    if (e.internalNode.srcToken.type !== "flow-collection")
      return null;
    const t = e.internalNode.srcToken, n = t.start.type === "flow-map-start" ? "block-map" : "block-seq", r = e.parent.type, s = {
      type: n,
      offset: t.offset,
      indent: t.indent,
      items: []
    };
    for (const i of t.items)
      or(i, ({ key: a, sep: o, value: l }) => {
        if (n === "block-map") {
          const u = [{ type: "space", indent: 0, offset: a.offset, source: this.indentation }];
          r === "property" && u.unshift({ type: "newline", indent: 0, offset: a.offset, source: `
` }), s.items.push({
            start: u,
            key: a,
            sep: o,
            value: l
          });
        } else n === "block-seq" && s.items.push({
          start: [
            { type: "newline", indent: 0, offset: l.offset, source: `
` },
            { type: "space", indent: 0, offset: l.offset, source: this.indentation },
            { type: "seq-item-ind", indent: 0, offset: l.offset, source: "-" },
            { type: "space", indent: 0, offset: l.offset, source: " " }
          ],
          value: l
        });
        if (l.type === "flow-collection")
          return Me.SKIP;
      });
    return im(s);
  }
}, f6 = structuredClone, h6 = class {
  constructor(e) {
    this.clientCapabilities = e, this.indentation = "  ";
  }
  configure(e) {
    this.indentation = e.indentation;
  }
  getCodeAction(e, t) {
    if (!t.context.diagnostics)
      return;
    const n = [];
    return n.push(...this.getConvertToBooleanActions(t.context.diagnostics, e)), n.push(...this.getJumpToSchemaActions(t.context.diagnostics)), n.push(...this.getTabToSpaceConverting(t.context.diagnostics, e)), n.push(...this.getUnusedAnchorsDelete(t.context.diagnostics, e)), n.push(...this.getConvertToBlockStyleActions(t.context.diagnostics, e)), n.push(...this.getKeyOrderActions(t.context.diagnostics, e)), n.push(...this.getQuickFixForPropertyOrValueMismatch(t.context.diagnostics, e)), n;
  }
  getJumpToSchemaActions(e) {
    var t, n, r, s, i;
    if (!((s = (r = (n = (t = this.clientCapabilities) == null ? void 0 : t.window) == null ? void 0 : n.showDocument) == null ? void 0 : r.support) != null ? s : !1))
      return [];
    const o = /* @__PURE__ */ new Map();
    for (const u of e) {
      const f = ((i = u.data) == null ? void 0 : i.schemaUri) || [];
      for (const c of f)
        c && (o.has(c) || o.set(c, []), o.get(c).push(u));
    }
    const l = [];
    for (const u of o.keys()) {
      const f = qt.create(`Jump to schema location (${nr.basename(u)})`, ir.create("JumpToSchema", ba.JUMP_TO_SCHEMA, u));
      f.diagnostics = o.get(u), l.push(f);
    }
    return l;
  }
  getTabToSpaceConverting(e, t) {
    const n = [], r = new cr(t), s = [];
    for (const i of e)
      if (i.message === "Using tabs can lead to unpredictable results") {
        if (s.includes(i.range.start.line))
          continue;
        const a = r.getLineContent(i.range.start.line);
        let o = 0, l = "";
        for (let f = i.range.start.character; f <= i.range.end.character && a.charAt(f) === "	"; f++)
          o++, l += this.indentation;
        s.push(i.range.start.line);
        let u = i.range;
        o !== i.range.end.character - i.range.start.character && (u = ie.create(i.range.start, Ye.create(i.range.end.line, i.range.start.character + o))), n.push(qt.create("Convert Tab to Spaces", Vn(t.uri, [_e.replace(u, l)]), on.QuickFix));
      }
    if (n.length !== 0) {
      const i = [];
      for (let a = 0; a <= r.getLineCount(); a++) {
        const o = r.getLineContent(a);
        let l = 0, u = "";
        for (let f = 0; f < o.length; f++) {
          const c = o.charAt(f);
          if (c !== " " && c !== "	") {
            l !== 0 && (i.push(_e.replace(ie.create(a, f - l, a, f), u)), l = 0, u = "");
            break;
          }
          if (c === " " && l !== 0) {
            i.push(_e.replace(ie.create(a, f - l, a, f), u)), l = 0, u = "";
            continue;
          }
          c === "	" && (u += this.indentation, l++);
        }
        l !== 0 && i.push(_e.replace(ie.create(a, 0, a, r.getLineLength(a)), u));
      }
      i.length > 0 && n.push(qt.create("Convert all Tabs to Spaces", Vn(t.uri, i), on.QuickFix));
    }
    return n;
  }
  getUnusedAnchorsDelete(e, t) {
    const n = [], r = new cr(t);
    for (const s of e)
      if (s.message.startsWith("Unused anchor") && s.source === Ha) {
        const i = ie.create(s.range.start, s.range.end), a = r.getText(i), o = r.getLineContent(i.end.line), l = e5(o, i.end.character);
        i.end.character = l;
        const u = qt.create(`Delete unused anchor: ${a}`, Vn(t.uri, [_e.del(i)]), on.QuickFix);
        u.diagnostics = [s], n.push(u);
      }
    return n;
  }
  getConvertToBooleanActions(e, t) {
    const n = [];
    for (const r of e)
      if (r.message === 'Incorrect type. Expected "boolean".') {
        const s = t.getText(r.range).toLocaleLowerCase();
        if (s === '"true"' || s === '"false"' || s === "'true'" || s === "'false'") {
          const i = s.includes("true") ? "true" : "false";
          n.push(qt.create("Convert to boolean", Vn(t.uri, [_e.replace(r.range, i)]), on.QuickFix));
        }
      }
    return n;
  }
  getConvertToBlockStyleActions(e, t) {
    const n = [];
    for (const r of e)
      if (r.code === "flowMap" || r.code === "flowSeq") {
        const s = Kd(t, r);
        if (Ve(s.internalNode) || Be(s.internalNode)) {
          const i = Ve(s.internalNode) ? "map" : "sequence", a = new c6(this.indentation);
          n.push(qt.create(`Convert to block style ${i}`, Vn(t.uri, [_e.replace(r.range, a.write(s))]), on.QuickFix));
        }
      }
    return n;
  }
  getKeyOrderActions(e, t) {
    var n, r, s, i, a, o, l, u, f, c, d, v, D, S;
    const x = [];
    for (const N of e)
      if (N?.code === "mapKeyOrder") {
        let k = Kd(t, N);
        for (; k && k.type !== "object"; )
          k = k.parent;
        if (k && Ve(k.internalNode)) {
          const y = f6(k.internalNode);
          if ((y.srcToken.type === "block-map" || y.srcToken.type === "flow-collection") && (k.internalNode.srcToken.type === "block-map" || k.internalNode.srcToken.type === "flow-collection")) {
            y.srcToken.items.sort((h, m) => {
              if (h.key && m.key && io(h.key) && io(m.key))
                return h.key.source.localeCompare(m.key.source);
              if (!h.key && m.key)
                return -1;
              if (h.key && !m.key)
                return 1;
              if (!h.key && !m.key)
                return 0;
            });
            for (let h = 0; h < y.srcToken.items.length; h++) {
              const m = y.srcToken.items[h], p = k.internalNode.srcToken.items[h];
              if (m.start = p.start, ((n = m.value) == null ? void 0 : n.type) === "alias" || ((r = m.value) == null ? void 0 : r.type) === "scalar" || ((s = m.value) == null ? void 0 : s.type) === "single-quoted-scalar" || ((i = m.value) == null ? void 0 : i.type) === "double-quoted-scalar") {
                const E = (l = (o = (a = m.value) == null ? void 0 : a.end) == null ? void 0 : o.findIndex((L) => L.type === "newline")) != null ? l : -1;
                let w = null;
                ((u = p.value) == null ? void 0 : u.type) === "block-scalar" ? w = (c = (f = p.value) == null ? void 0 : f.props) == null ? void 0 : c.find((L) => L.type === "newline") : io(p.value) && (w = (v = (d = p.value) == null ? void 0 : d.end) == null ? void 0 : v.find((L) => L.type === "newline")), w && E < 0 && (m.value.end = (D = m.value.end) != null ? D : [], m.value.end.push(w)), !w && E > -1 && m.value.end.splice(E, 1);
              } else ((S = m.value) == null ? void 0 : S.type) === "block-scalar" && (m.value.props.find((w) => w.type === "newline") || m.value.props.push({ type: "newline", indent: 0, offset: m.value.offset, source: `
` }));
            }
          }
          const b = ie.create(t.positionAt(k.offset), t.positionAt(k.offset + k.length));
          x.push(qt.create("Fix key order for this map", Vn(t.uri, [_e.replace(b, im(y.srcToken))]), on.QuickFix));
        }
      }
    return x;
  }
  /**
   * Check if diagnostic contains info for quick fix
   * Supports Enum/Const/Property mismatch
   */
  getPossibleQuickFixValues(e) {
    if (typeof e.data == "object") {
      if (e.code === ct.EnumValueMismatch && "values" in e.data && Array.isArray(e.data.values))
        return e.data.values;
      if (e.code === ct.PropertyExpected && "properties" in e.data && Array.isArray(e.data.properties))
        return e.data.properties;
    }
  }
  getQuickFixForPropertyOrValueMismatch(e, t) {
    const n = [];
    for (const r of e) {
      const s = this.getPossibleQuickFixValues(r);
      if (s?.length)
        for (const i of s)
          n.push(qt.create(i, Vn(t.uri, [_e.replace(r.range, i)]), on.QuickFix));
    }
    return n;
  }
};
function Kd(e, t) {
  const n = It.getYamlDocument(e), r = e.offsetAt(t.range.start);
  return Wa(r, n).getNodeFromOffset(r);
}
function Vn(e, t) {
  const n = {};
  return n[e] = t, {
    changes: n
  };
}
function d6(e, t) {
  const { position: n } = t, r = new cr(e);
  if (t.ch === `
`) {
    const s = r.getLineContent(n.line - 1);
    if (s.trimRight().endsWith(":")) {
      const i = r.getLineContent(n.line), a = i.substring(n.character, i.length), o = s.indexOf(" - ") !== -1;
      if (a.trimRight().length === 0) {
        const l = n.character - (s.length - s.trimLeft().length);
        if (l === t.options.tabSize && !o)
          return;
        const u = [];
        return i.length > 0 && u.push(_e.del(ie.create(n, Ye.create(n.line, i.length - 1)))), u.push(_e.insert(n, " ".repeat(t.options.tabSize + (o ? 2 - l : 0)))), u;
      }
      if (o)
        return [_e.insert(n, " ".repeat(t.options.tabSize))];
    }
    if (s.trimRight().endsWith("|"))
      return [_e.insert(n, " ".repeat(t.options.tabSize))];
    if (s.includes(" - ") && !s.includes(": "))
      return [_e.insert(n, "- ")];
    if (s.includes(" - ") && s.includes(": "))
      return [_e.insert(n, "  ")];
  }
}
function m6(e) {
  const t = /* @__PURE__ */ new Map();
  return e && (e.url ? e.url.startsWith("schemaservice://combinedSchema/") ? Xd(e, t) : t.set(e.url, e) : Xd(e, t)), t;
}
function Xd(e, t) {
  e.allOf && Ao(e.allOf, t), e.anyOf && Ao(e.anyOf, t), e.oneOf && Ao(e.oneOf, t);
}
function Ao(e, t) {
  for (const n of e)
    !Ir(n) && n.url && !t.has(n.url) && t.set(n.url, n);
}
var p6 = class {
  constructor(e, t) {
    this.schemaService = e, this.telemetry = t;
  }
  async getCodeLens(e) {
    var t;
    const n = [];
    try {
      const r = It.getYamlDocument(e);
      let s = /* @__PURE__ */ new Map();
      for (const i of r.documents) {
        const a = await this.schemaService.getSchemaForResource(e.uri, i);
        a?.schema && (s = new Map([...m6(a?.schema), ...s]));
      }
      for (const i of s) {
        const a = bl.create(ie.create(0, 0, 0, 0));
        a.command = {
          title: eg(i[1], i[0]),
          command: ba.JUMP_TO_SCHEMA,
          arguments: [i[0]]
        }, n.push(a);
      }
    } catch (r) {
      (t = this.telemetry) == null || t.sendError("yaml.codeLens.error", r);
    }
    return n;
  }
  resolveCodeLens(e) {
    return e;
  }
}, g6 = class {
  constructor() {
    this.spacesDiff = 0, this.looksLikeAlignment = !1;
  }
};
function y6(e, t, n, r, s) {
  s.spacesDiff = 0, s.looksLikeAlignment = !1;
  let i;
  for (i = 0; i < t && i < r; i++) {
    const d = e.charCodeAt(i), v = n.charCodeAt(i);
    if (d !== v)
      break;
  }
  let a = 0, o = 0;
  for (let d = i; d < t; d++)
    e.charCodeAt(d) === 32 ? a++ : o++;
  let l = 0, u = 0;
  for (let d = i; d < r; d++)
    n.charCodeAt(d) === 32 ? l++ : u++;
  if (a > 0 && o > 0 || l > 0 && u > 0)
    return;
  const f = Math.abs(o - u), c = Math.abs(a - l);
  if (f === 0) {
    s.spacesDiff = c, c > 0 && 0 <= l - 1 && l - 1 < e.length && l < n.length && n.charCodeAt(l) !== 32 && e.charCodeAt(l - 1) === 32 && e.charCodeAt(e.length - 1) === 44 && (s.looksLikeAlignment = !0);
    return;
  }
  c % f === 0 && (s.spacesDiff = c / f);
}
function b6(e, t, n) {
  const r = Math.min(e.getLineCount(), 1e4);
  let s = 0, i = 0, a = "", o = 0;
  const l = [2, 4, 6, 8, 3, 5, 7], u = 8, f = [0, 0, 0, 0, 0, 0, 0, 0, 0], c = new g6();
  for (let D = 1; D <= r; D++) {
    const S = e.getLineLength(D), x = e.getLineContent(D), N = S <= 65536;
    let k = !1, y = 0, b = 0, h = 0;
    for (let p = 0, E = S; p < E; p++) {
      const w = N ? x.charCodeAt(p) : e.getLineCharCode(D, p);
      if (w === 9)
        h++;
      else if (w === 32)
        b++;
      else {
        k = !0, y = p;
        break;
      }
    }
    if (!k || (h > 0 ? s++ : b > 1 && i++, y6(a, o, x, y, c), c.looksLikeAlignment && t !== c.spacesDiff))
      continue;
    const m = c.spacesDiff;
    m <= u && f[m]++, a = x, o = y;
  }
  let d = n;
  s !== i && (d = s < i);
  let v = t;
  if (d) {
    let D = d ? 0 : 0.1 * r;
    l.forEach((S) => {
      const x = f[S];
      x > D && (D = x, v = S);
    }), v === 4 && f[4] > 0 && f[2] > 0 && f[2] >= f[4] / 2 && (v = 2);
  }
  return {
    insertSpaces: d,
    tabSize: v
  };
}
function qi(e, t, n, r, s = 0, i = 0) {
  if (e !== null && typeof e == "object") {
    const a = s === 0 && r.shouldIndentWithTab || s > 0 ? t + r.indentation : "";
    if (Array.isArray(e)) {
      if (i += 1, e.length === 0)
        return "";
      let o = "";
      for (let l = 0; l < e.length; l++) {
        let u = e[l];
        if (typeof e[l] != "object") {
          o += `
` + a + "- " + n(e[l]);
          continue;
        }
        Array.isArray(e[l]) || (u = v6(e[l], i)), o += qi(u, t, n, r, s += 1, i);
      }
      return o;
    } else {
      const o = Object.keys(e);
      if (o.length === 0)
        return "";
      let l = s === 0 && r.newLineFirst || s > 0 ? `
` : "", u = !0;
      for (let f = 0; f < o.length; f++) {
        const c = o[f];
        if (s === 0 && r.existingProps.includes(c))
          continue;
        const d = typeof e[c] == "object", v = d ? ":" : ": ", D = d && /^\s|-/.test(c) ? r.indentation : "", S = a + D, x = u ? "" : `
`;
        if (s === 0 && u && !r.indentFirstObject) {
          const N = qi(e[c], S, n, r, s + 1, 0);
          l += x + t + c + v + N;
        } else {
          const N = qi(e[c], S, n, r, s + 1, 0);
          l += x + a + c + v + N;
        }
        u = !1;
      }
      return l;
    }
  }
  return n(e);
}
function v6(e, t) {
  const n = {};
  for (let r = 0; r < Object.keys(e).length; r++) {
    const s = Object.keys(e)[r];
    r === 0 ? n["- ".repeat(t) + s] = e[s] : n["  ".repeat(t) + s] = e[s];
  }
  return n;
}
var w6 = ps(), Zd = /[\\]+"/g, e1 = pt.Class, xi = "__", D6 = class {
  constructor(e, t = {}, n, r) {
    this.schemaService = e, this.clientCapabilities = t, this.yamlDocument = n, this.telemetry = r, this.completionEnabled = !0, this.arrayPrefixIndentation = "", this.isNumberExp = /^\d+$/;
  }
  configure(e, t) {
    var n;
    e && (this.completionEnabled = e.completion), this.customTags = e.customTags, this.yamlVersion = e.yamlVersion, this.isSingleQuote = ((n = t?.yamlFormatterSettings) == null ? void 0 : n.singleQuote) || !1, this.configuredIndentation = e.indentation, this.disableDefaultProperties = e.disableDefaultProperties, this.parentSkeletonSelectedFirst = e.parentSkeletonSelectedFirst;
  }
  async doComplete(e, t, n = !1, r = !0) {
    var s;
    const i = yl.create([], !1);
    if (!this.completionEnabled)
      return i;
    const a = this.yamlDocument.getYamlDocument(e, { customTags: this.customTags, yamlVersion: this.yamlVersion }, !0), o = new cr(e);
    if (this.configuredIndentation)
      this.indentation = this.configuredIndentation;
    else {
      const h = b6(o, 2, !0);
      this.indentation = h.insertSpaces ? " ".repeat(h.tabSize) : "	";
    }
    mg(a.documents, n);
    for (const h of a.documents)
      h.uri = e.uri;
    const l = e.offsetAt(t), u = e.getText();
    if (u.charAt(l - 1) === ":")
      return Promise.resolve(i);
    let f = Wa(l, a);
    if (f === null)
      return Promise.resolve(i);
    f = f.clone();
    let [c, d] = f.getNodeFromPosition(l, o, this.indentation.length);
    const v = this.getCurrentWord(e, l);
    let D = o.getLineContent(t.line);
    const S = D.substring(t.character), x = /^[ ]+\n?$/.test(S);
    this.arrayPrefixIndentation = "";
    let N = null;
    if (x) {
      N = ie.create(t, Ye.create(t.line, D.length));
      const h = D.trim().length === 0, m = D.match(/^\s*(-)\s*$/);
      if (c && ae(c) && !h && !m) {
        const p = D.substring(0, t.character), E = (
          // get indentation of unfinished property (between indent and cursor)
          p.match(/^[\s-]*([^:]+)?$/) || // OR get unfinished value (between colon and cursor)
          p.match(/:[ \t]((?!:[ \t]).*)$/)
        );
        E?.[1] && (N = ie.create(Ye.create(t.line, t.character - E[1].length), Ye.create(t.line, D.length)));
      }
    } else if (c && ae(c) && c.value === "null") {
      const h = e.positionAt(c.range[0]);
      h.character += 1;
      const m = e.positionAt(c.range[2]);
      m.character += 1, N = ie.create(h, m);
    } else if (c && ae(c) && c.value) {
      const h = e.positionAt(c.range[0]);
      N = ie.create(h, e.positionAt(c.range[1]));
    } else if (c && ae(c) && c.value === null && v === "-")
      N = ie.create(t, t), this.arrayPrefixIndentation = " ";
    else {
      let h = l - v.length;
      h > 0 && u[h - 1] === '"' && h--, N = ie.create(e.positionAt(h), t);
    }
    const k = {}, y = {
      add: (h, m) => {
        const p = function(A) {
          var _;
          if (((_ = k[A.label]) == null ? void 0 : _.label) === xi)
            return;
          const T = A.parent.schema, P = Gl(T), V = T.markdownDescription || T.description;
          let Y = i.items.find((K) => {
            var J;
            return ((J = K.parent) == null ? void 0 : J.schema) === T && K.kind === e1;
          });
          Y && Y.parent.insertTexts.includes(A.insertText) || (Y ? Y.parent.insertTexts.push(A.insertText) : (Y = {
            ...A,
            label: P,
            documentation: V,
            sortText: "_" + P,
            kind: e1
          }, Y.label = Y.label || A.label, Y.parent.insertTexts = [A.insertText], i.items.push(Y)));
        }, E = !!h.parent;
        let w = h.label;
        if (!w) {
          console.warn(`Ignoring CompletionItem without label: ${JSON.stringify(h)}`);
          return;
        }
        if (pa(w) || (w = String(w)), w = w.replace(/[\n]/g, "↵"), w.length > 60) {
          const A = w.substr(0, 57).trim() + "...";
          k[A] || (w = A);
        }
        if (h.label.toLowerCase() === "regular expression") {
          const _ = h.documentation.value.split(":");
          w = _.length > 0 ? `${this.getQuote()}\\${JSON.parse(_[1])}${this.getQuote()}` : h.label, h.insertText = w, h.textEdit = _e.replace(N, w);
        } else {
          let A = h.insertText.replace(/\${[0-9]+[:|](.*)}/g, (T, P) => P).replace(/\$([0-9]+)/g, "");
          const _ = A.split(":");
          let O = _.length > 1 ? _[1].trim() : A;
          O && /^(['\\"\\])$/.test(O) && (O = `${this.getQuote()}\\${O}${this.getQuote()}`, A = _.length > 1 ? _[0] + ": " + O : O, h.insertText = A), h.insertText.endsWith("$1") && !E && (h.insertText = h.insertText.substr(0, h.insertText.length - 2)), N && N.start.line === N.end.line && (h.textEdit = _e.replace(N, h.insertText));
        }
        if (h.label = w, E) {
          p(h);
          return;
        }
        this.arrayPrefixIndentation && this.updateCompletionText(h, this.arrayPrefixIndentation + h.insertText);
        const L = k[w], C = L?.label !== xi && L?.insertText !== h.insertText;
        if (!L)
          k[w] = h, i.items.push(h);
        else if (C) {
          const A = this.mergeSimpleInsertTexts(w, L.insertText, h.insertText, m);
          A ? this.updateCompletionText(L, A) : (k[w] = h, i.items.push(h));
        }
        L && !L.documentation && h.documentation && (L.documentation = h.documentation);
      },
      error: (h) => {
        var m;
        (m = this.telemetry) == null || m.sendError("yaml.completion.error", h);
      },
      log: (h) => {
        console.log(h);
      },
      getNumberOfProposals: () => i.items.length,
      result: i,
      proposed: k
    };
    this.customTags && this.customTags.length > 0 && this.getCustomTagValueCompletions(y), D.endsWith(`
`) && (D = D.substr(0, D.length - 1));
    try {
      const h = await this.schemaService.getSchemaForResource(e.uri, f);
      if ((!h || h.errors.length) && t.line === 0 && t.character === 0 && !Zl(D)) {
        const w = {
          kind: pt.Text,
          label: "Inline schema",
          insertText: "# yaml-language-server: $schema=",
          insertTextFormat: ze.PlainText
        };
        i.items.push(w);
      }
      if (Zl(D) || I5(a.tokens, l)) {
        const w = D.indexOf("$schema=");
        return w !== -1 && w + 8 <= t.character && this.schemaService.getAllSchemas().forEach((L) => {
          var C;
          const A = {
            kind: pt.Constant,
            label: (C = L.name) != null ? C : L.uri,
            detail: L.description,
            insertText: L.uri,
            insertTextFormat: ze.PlainText,
            insertTextMode: pl.asIs
          };
          i.items.push(A);
        }), i;
      }
      if (!h || h.errors.length)
        return i;
      let m = null;
      if (!c)
        if (!f.internalDocument.contents || ae(f.internalDocument.contents)) {
          const w = f.internalDocument.createNode({});
          w.range = [l, l + 1, l + 1], f.internalDocument.contents = w, f.updateFromInternalDocument(), c = w;
        } else
          c = f.findClosestNode(l, o), d = !0;
      const p = c;
      if (c)
        if (D.length === 0)
          c = f.internalDocument.contents;
        else {
          const w = f.getParent(c);
          if (w) {
            if (ae(c)) {
              if (c.value) {
                if (Ae(w)) {
                  if (w.value === c) {
                    if (D.trim().length > 0 && D.indexOf(":") < 0) {
                      const L = this.createTempObjNode(v, c, f), C = f.getParent(w);
                      if (Be(f.internalDocument.contents)) {
                        const A = P5(f.internalDocument.contents, w);
                        typeof A == "number" && (f.internalDocument.set(A, L), f.updateFromInternalDocument());
                      } else C && (Ve(C) || Be(C)) ? (C.set(w.key, L), f.updateFromInternalDocument()) : (f.internalDocument.set(w.key, L), f.updateFromInternalDocument());
                      m = L.items[0], c = L;
                    } else if (D.trim().length === 0) {
                      const L = f.getParent(w);
                      L && (c = L);
                    }
                  } else if (w.key === c) {
                    const L = f.getParent(w);
                    m = w, L && (c = L);
                  }
                } else if (Be(w))
                  if (D.trim().length > 0) {
                    const L = this.createTempObjNode(v, c, f);
                    w.delete(c), w.add(L), f.updateFromInternalDocument(), c = L;
                  } else
                    c = w;
              } else if (c.value === null) {
                if (Ae(w)) {
                  if (w.key === c)
                    c = w;
                  else if (De(w.key) && w.key.range) {
                    const L = f.getParent(w);
                    if (d && L && Ve(L) && R5(L))
                      c = L;
                    else {
                      const C = e.positionAt(w.key.range[0]);
                      if (t.character > C.character && t.line !== C.line) {
                        const A = this.createTempObjNode(v, c, f);
                        L && (Ve(L) || Be(L)) ? (L.set(w.key, A), f.updateFromInternalDocument()) : (f.internalDocument.set(w.key, A), f.updateFromInternalDocument()), m = A.items[0], c = A;
                      } else C.character === t.character && L && (c = L);
                    }
                  }
                } else if (Be(w))
                  if (D.charAt(t.character - 1) !== "-") {
                    const L = this.createTempObjNode(v, c, f);
                    w.delete(c), w.add(L), f.updateFromInternalDocument(), c = L;
                  } else if (D.charAt(t.character - 1) === "-") {
                    const L = this.createTempObjNode("", c, f);
                    w.delete(c), w.add(L), f.updateFromInternalDocument(), c = L;
                  } else
                    c = w;
              }
            } else if (Ve(c) && !d && D.trim().length === 0 && Be(w)) {
              const L = o.getLineContent(t.line + 1);
              (o.getLineCount() === t.line + 1 || L.trim().length === 0) && (c = w);
            }
          } else if (ae(c)) {
            const L = this.createTempObjNode(v, c, f);
            f.internalDocument.contents = L, f.updateFromInternalDocument(), m = L.items[0], c = L;
          } else if (Ve(c))
            for (const L of c.items)
              De(L.value) && L.value.range && L.value.range[0] === l + 1 && (c = L.value);
          else if (Be(c) && D.charAt(t.character - 1) !== "-") {
            const L = this.createTempObjNode(v, c, f);
            L.items = [], f.updateFromInternalDocument();
            for (const C of c.items)
              Ve(C) && C.items.forEach((A) => {
                L.items.push(A);
              });
            c = L;
          }
        }
      if (c && Ve(c)) {
        const w = c.items;
        for (const L of w)
          (!m || m !== L) && ae(L.key) && (k[L.key.value + ""] = gl.create(xi));
        this.addPropertyCompletions(h, f, c, p, "", y, o, N, r), !h && v.length > 0 && u.charAt(l - v.length - 1) !== '"' && y.add({
          kind: pt.Property,
          label: v,
          insertText: this.getInsertTextForProperty(v, null, ""),
          insertTextFormat: ze.Snippet
        });
      }
      const E = {};
      this.getValueCompletions(h, f, c, l, e, y, E, r);
    } catch (h) {
      (s = this.telemetry) == null || s.sendError("yaml.completion.error", h);
    }
    this.finalizeParentCompletion(i);
    const b = i.items.filter((h, m, p) => m === p.findIndex((E) => E.label === h.label && E.insertText === h.insertText && E.kind === h.kind));
    return b?.length > 0 && (i.items = b), i;
  }
  updateCompletionText(e, t) {
    e.insertText = t, e.textEdit && (e.textEdit.newText = t);
  }
  mergeSimpleInsertTexts(e, t, n, r) {
    const s = (f) => f.includes(`
`), i = (f) => f.startsWith(`
`), a = (f) => {
      const c = f.indexOf(`
`);
      return c > 0 && f.substring(c, f.length).trim().length === 0;
    };
    if (s(t) || s(n))
      return r && a(t) && !a(n) && !i(n) ? n : void 0;
    const o = this.getValuesFromInsertText(t), l = this.getValuesFromInsertText(n), u = Array.prototype.concat(o, l);
    if (u.length)
      return u.length === 1 ? `${e}: \${1:${u[0]}}` : `${e}: \${1|${u.join(",")}|}`;
  }
  getValuesFromInsertText(e) {
    const t = e.substring(e.indexOf(":") + 1).trim();
    if (!t)
      return [];
    const n = t.match(/^\${1[|:]([^|]*)+\|?}$/);
    return n ? n[1].split(",") : [t];
  }
  finalizeParentCompletion(e) {
    const t = (n) => {
      let r = 0;
      return n.map((s) => {
        const i = s.match(/\$([0-9]+)|\${[0-9]+:/g);
        if (!i)
          return s;
        const a = i.map((l) => +l.replace(/\${([0-9]+)[:|]/g, "$1").replace("$", "")).reduce((l, u) => u > l ? u : l, 0), o = s.replace(/\$([0-9]+)/g, (l, u) => "$" + (+u + r)).replace(/\${([0-9]+)[:|]/g, (l, u) => "${" + (+u + r) + ":");
        return r += a, o;
      });
    };
    e.items.forEach((n) => {
      if (this.isParentCompletionItem(n)) {
        const r = n.parent.indent || "";
        let i = t(n.parent.insertTexts).join(`
${r}`);
        i.endsWith("$1") && (i = i.substring(0, i.length - 2)), n.insertText = this.arrayPrefixIndentation + i, n.textEdit && (n.textEdit.newText = n.insertText);
        const a = i.replace(/\${[0-9]+[:|](.*)}/g, (l, u) => u).replace(/\$([0-9]+)/g, ""), o = n.documentation ? [n.documentation, "", "----", ""] : [];
        n.documentation = {
          kind: hn.Markdown,
          value: [...o, "```yaml", r + a, "```"].join(`
`)
        }, delete n.parent;
      }
    });
  }
  createTempObjNode(e, t, n) {
    const r = {};
    r[e] = null;
    const s = n.internalDocument.createNode(r);
    return s.range = t.range, s.items[0].key.range = t.range, s.items[0].value.range = t.range, s;
  }
  addPropertyCompletions(e, t, n, r, s, i, a, o, l) {
    var u, f, c;
    const d = t.getMatchingSchemas(e.schema, -1, null, l), v = a.getText(o), D = a.getLineContent(o.start.line), S = D.trim().length === 0, x = D.indexOf(":") !== -1, N = D.trimLeft().indexOf("-") === 0, k = t.getParent(n), y = d.find((m) => m.node.internalNode === r && m.schema.properties), b = d.filter((m) => m.schema.oneOf).map((m) => m.schema.oneOf)[0];
    let h = !1;
    b?.length < d.length && b?.forEach((m, p) => {
      var E, w;
      !((E = d[p]) != null && E.schema.oneOf) && ((w = d[p]) == null ? void 0 : w.schema.properties) === m.properties && (h = !0);
    });
    for (const m of d) {
      if ((m.node.internalNode === n && !y || m.node.internalNode === r && !x || ((u = m.node.parent) == null ? void 0 : u.internalNode) === r && !x) && !m.inverted) {
        this.collectDefaultSnippets(m.schema, s, i, {
          newLineFirst: !1,
          indentFirstObject: !1,
          shouldIndentWithTab: N
        });
        const p = m.schema.properties;
        if (p) {
          const E = m.schema.maxProperties;
          if (E === void 0 || n.items === void 0 || n.items.length < E || n.items.length === E && !S) {
            for (const w in p)
              if (Object.prototype.hasOwnProperty.call(p, w)) {
                const L = p[w];
                if (typeof L == "object" && !L.deprecationMessage && !L.doNotSuggest) {
                  let C = "";
                  if (k && Be(k) && n.items.length <= 1 && !S) {
                    const P = a.getText(), V = P.lastIndexOf("-", n.range[0] - 1);
                    if (V >= 0) {
                      const Y = o.end.character - o.start.character;
                      C = " " + P.slice(V + 1, n.range[1] - Y);
                    }
                  }
                  C += this.arrayPrefixIndentation;
                  let A;
                  L.type === "array" && (A = n.items.find((P) => ae(P.key) && P.key.range && P.key.value === w && ae(P.value) && !P.value.value && a.getPosition(P.key.range[2]).line === o.end.line - 1)) && A && (Array.isArray(L.items) ? this.addSchemaValueCompletions(L.items[0], s, i, {}, "property") : typeof L.items == "object" && L.items.type === "object" && this.addArrayItemValueCompletion(L.items, s, i));
                  let _ = w;
                  (!w.startsWith(v) || !x) && (_ = this.getInsertTextForProperty(w, L, s, C + this.indentation));
                  const O = ae(r) && r.value === null || Ve(r) && r.items.length === 0, T = ((f = m.schema.required) == null ? void 0 : f.length) > 0;
                  (!this.parentSkeletonSelectedFirst || !O || !T) && i.add({
                    kind: pt.Property,
                    label: w,
                    insertText: _,
                    insertTextFormat: ze.Snippet,
                    documentation: this.fromMarkup(L.markdownDescription) || L.description || ""
                  }, h), (c = m.schema.required) != null && c.includes(w) && i.add({
                    label: w,
                    insertText: this.getInsertTextForProperty(w, L, s, C + this.indentation),
                    insertTextFormat: ze.Snippet,
                    documentation: this.fromMarkup(L.markdownDescription) || L.description || "",
                    parent: {
                      schema: m.schema,
                      indent: C
                    }
                  });
                }
              }
          }
        }
        if (k && Be(k) && n5(m.schema) && this.addSchemaValueCompletions(m.schema, s, i, {}, "property", Array.isArray(k.items)), m.schema.propertyNames && m.schema.additionalProperties && m.schema.type === "object") {
          const E = Qe(m.schema.propertyNames);
          if (!E.deprecationMessage && !E.doNotSuggest) {
            const w = E.title || "property";
            i.add({
              kind: pt.Property,
              label: w,
              insertText: `\${1:${w}}: `,
              insertTextFormat: ze.Snippet,
              documentation: this.fromMarkup(E.markdownDescription) || E.description || ""
            });
          }
        }
      }
      k && m.node.internalNode === k && m.schema.defaultSnippets && (n.items.length === 1 ? this.collectDefaultSnippets(m.schema, s, i, {
        newLineFirst: !1,
        indentFirstObject: !1,
        shouldIndentWithTab: !0
      }, 1) : this.collectDefaultSnippets(m.schema, s, i, {
        newLineFirst: !1,
        indentFirstObject: !0,
        shouldIndentWithTab: !1
      }, 1));
    }
  }
  getValueCompletions(e, t, n, r, s, i, a, o) {
    let l = null;
    if (n && ae(n) && (n = t.getParent(n)), !n) {
      this.addSchemaValueCompletions(e.schema, "", i, a, "value");
      return;
    }
    if (Ae(n)) {
      const u = n.value;
      if (u && u.range && r > u.range[0] + u.range[2])
        return;
      l = ae(n.key) ? n.key.value + "" : null, n = t.getParent(n);
    }
    if (n && (l !== null || Be(n))) {
      const f = t.getMatchingSchemas(e.schema, -1, null, o);
      for (const c of f)
        if (c.node.internalNode === n && !c.inverted && c.schema) {
          if (c.schema.items && (this.collectDefaultSnippets(c.schema, "", i, {
            newLineFirst: !1,
            indentFirstObject: !1,
            shouldIndentWithTab: !1
          }), Be(n) && n.items))
            if (Array.isArray(c.schema.items)) {
              const d = this.findItemAtOffset(n, s, r);
              d < c.schema.items.length && this.addSchemaValueCompletions(c.schema.items[d], "", i, a, "value");
            } else typeof c.schema.items == "object" && (c.schema.items.type === "object" || Jl(c.schema.items)) ? this.addSchemaValueCompletions(c.schema.items, "", i, a, "value", !0) : this.addSchemaValueCompletions(c.schema.items, "", i, a, "value");
          if (c.schema.properties) {
            const d = c.schema.properties[l];
            d && this.addSchemaValueCompletions(d, "", i, a, "value");
          }
          c.schema.additionalProperties && this.addSchemaValueCompletions(c.schema.additionalProperties, "", i, a, "value");
        }
      a.boolean && (this.addBooleanValueCompletion(!0, "", i), this.addBooleanValueCompletion(!1, "", i)), a.null && this.addNullValueCompletion("", i);
    }
  }
  addArrayItemValueCompletion(e, t, n, r) {
    const s = Gl(e), i = `- ${this.getInsertTextForObject(e, t).insertText.trimLeft()}`, a = s ? " type `" + s + "`" : "", o = e.description ? " (" + e.description + ")" : "", l = this.getDocumentationWithMarkdownText(`Create an item of an array${a}${o}`, i);
    n.add({
      kind: this.getSuggestionKind(e.type),
      label: "- (array item) " + (s || r),
      documentation: l,
      insertText: i,
      insertTextFormat: ze.Snippet
    });
  }
  getInsertTextForProperty(e, t, n, r = this.indentation) {
    const s = this.getInsertTextForValue(e, "", "string"), i = s + ":";
    let a, o = 0;
    if (t) {
      let l = Array.isArray(t.type) ? t.type[0] : t.type;
      if (l || (t.properties ? l = "object" : t.items ? l = "array" : t.anyOf && (l = "anyOf")), Array.isArray(t.defaultSnippets)) {
        if (t.defaultSnippets.length === 1) {
          const u = t.defaultSnippets[0].body;
          Yn(u) && (a = this.getInsertTextForSnippetValue(u, "", {
            newLineFirst: !0,
            indentFirstObject: !1,
            shouldIndentWithTab: !1
          }, [], 1), !a.startsWith(" ") && !a.startsWith(`
`) && (a = " " + a));
        }
        o += t.defaultSnippets.length;
      }
      if (t.enum && (!a && t.enum.length === 1 && (a = " " + this.getInsertTextForGuessedValue(t.enum[0], "", l)), o += t.enum.length), t.const && (a || (a = this.getInsertTextForGuessedValue(t.const, "", l), a = this.evaluateTab1Symbol(a), a = " " + a), o++), Yn(t.default) && (a || (a = " " + this.getInsertTextForGuessedValue(t.default, "", l)), o++), Array.isArray(t.examples) && t.examples.length && (a || (a = " " + this.getInsertTextForGuessedValue(t.examples[0], "", l)), o += t.examples.length), t.properties)
        return `${i}
${this.getInsertTextForObject(t, n, r).insertText}`;
      if (t.items)
        return `${i}
${r}- ${this.getInsertTextForArray(t.items, n, 1, r).insertText}`;
      if (o === 0)
        switch (l) {
          case "boolean":
            a = " $1";
            break;
          case "string":
            a = " $1";
            break;
          case "object":
            a = `
${r}`;
            break;
          case "array":
            a = `
${r}- `;
            break;
          case "number":
          case "integer":
            a = " ${1:0}";
            break;
          case "null":
            a = " ${1:null}";
            break;
          case "anyOf":
            a = " $1";
            break;
          default:
            return s;
        }
    }
    return (!a || o > 1) && (a = " $1"), i + a + n;
  }
  getInsertTextForObject(e, t, n = this.indentation, r = 1) {
    let s = "";
    return e.properties ? (Object.keys(e.properties).forEach((i) => {
      const a = e.properties[i];
      let o = Array.isArray(a.type) ? a.type[0] : a.type;
      if (o || (a.anyOf && (o = "anyOf"), a.properties && (o = "object"), a.items && (o = "array")), e.required && e.required.indexOf(i) > -1)
        switch (o) {
          case "boolean":
          case "string":
          case "number":
          case "integer":
          case "anyOf": {
            let l = a.default || a.const;
            l ? (o === "string" && (l = this.convertToStringValue(l)), s += `${n}${i}: \${${r++}:${l}}
`) : s += `${n}${i}: $${r++}
`;
            break;
          }
          case "array":
            {
              const l = this.getInsertTextForArray(a.items, t, r++, n), u = l.insertText.split(`
`);
              let f = l.insertText;
              if (u.length > 1) {
                for (let c = 1; c < u.length; c++) {
                  const d = u[c];
                  u[c] = `  ${d}`;
                }
                f = u.join(`
`);
              }
              r = l.insertIndex, s += `${n}${i}:
${n}${this.indentation}- ${f}
`;
            }
            break;
          case "object":
            {
              const l = this.getInsertTextForObject(a, t, `${n}${this.indentation}`, r++);
              r = l.insertIndex, s += `${n}${i}:
${l.insertText}
`;
            }
            break;
        }
      else if (!this.disableDefaultProperties && a.default !== void 0)
        switch (o) {
          case "boolean":
          case "number":
          case "integer":
            s += `${n}${//added quote if key is null
            i === "null" ? this.getInsertTextForValue(i, "", "string") : i}: \${${r++}:${a.default}}
`;
            break;
          case "string":
            s += `${n}${i}: \${${r++}:${this.convertToStringValue(a.default)}}
`;
            break;
        }
    }), s.trim().length === 0 && (s = `${n}$${r++}
`), s = s.trimRight() + t, { insertText: s, insertIndex: r }) : (s = `${n}$${r++}
`, { insertText: s, insertIndex: r });
  }
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  getInsertTextForArray(e, t, n = 1, r = this.indentation) {
    let s = "";
    if (!e)
      return s = `$${n++}`, { insertText: s, insertIndex: n };
    let i = Array.isArray(e.type) ? e.type[0] : e.type;
    switch (i || (e.properties && (i = "object"), e.items && (i = "array")), e.type) {
      case "boolean":
        s = `\${${n++}:false}`;
        break;
      case "number":
      case "integer":
        s = `\${${n++}:0}`;
        break;
      case "string":
        s = `\${${n++}}`;
        break;
      case "object":
        {
          const a = this.getInsertTextForObject(e, t, `${r}  `, n++);
          s = a.insertText.trimLeft(), n = a.insertIndex;
        }
        break;
    }
    return { insertText: s, insertIndex: n };
  }
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  getInsertTextForGuessedValue(e, t, n) {
    switch (typeof e) {
      case "object":
        return e === null ? "${1:null}" + t : this.getInsertTextForValue(e, t, n);
      case "string": {
        let r = JSON.stringify(e);
        return r = r.substr(1, r.length - 2), r = this.getInsertTextForPlainText(r), n === "string" && (r = this.convertToStringValue(r)), "${1:" + r + "}" + t;
      }
      case "number":
      case "boolean":
        return "${1:" + e + "}" + t;
    }
    return this.getInsertTextForValue(e, t, n);
  }
  getInsertTextForPlainText(e) {
    return e.replace(/[\\$}]/g, "\\$&");
  }
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  getInsertTextForValue(e, t, n) {
    if (e === null)
      return "null";
    switch (typeof e) {
      case "object": {
        const r = this.indentation;
        return this.getInsertTemplateForValue(e, r, { index: 1 }, t);
      }
      case "number":
      case "boolean":
        return this.getInsertTextForPlainText(e + t);
    }
    return n = Array.isArray(n) ? n[0] : n, n === "string" && (e = this.convertToStringValue(e)), this.getInsertTextForPlainText(e + t);
  }
  getInsertTemplateForValue(e, t, n, r) {
    if (Array.isArray(e)) {
      let s = `
`;
      for (const i of e)
        s += `${t}- \${${n.index++}:${i}}
`;
      return s;
    } else if (typeof e == "object") {
      let s = `
`;
      for (const i in e)
        if (Object.prototype.hasOwnProperty.call(e, i)) {
          const a = e[i];
          s += `${t}\${${n.index++}:${i}}:`;
          let o;
          typeof a == "object" ? o = `${this.getInsertTemplateForValue(a, t + this.indentation, n, r)}` : o = ` \${${n.index++}:${this.getInsertTextForPlainText(a + r)}}
`, s += `${o}`;
        }
      return s;
    }
    return this.getInsertTextForPlainText(e + r);
  }
  addSchemaValueCompletions(e, t, n, r, s, i) {
    typeof e == "object" && (this.addEnumValueCompletions(e, t, n, i), this.addDefaultValueCompletions(e, t, n), this.collectTypes(e, r), i && s === "value" && !Jl(e) && this.addArrayItemValueCompletion(e, t, n), Array.isArray(e.allOf) && e.allOf.forEach((a) => this.addSchemaValueCompletions(a, t, n, r, s, i)), Array.isArray(e.anyOf) && e.anyOf.forEach((a) => this.addSchemaValueCompletions(a, t, n, r, s, i)), Array.isArray(e.oneOf) && e.oneOf.forEach((a) => this.addSchemaValueCompletions(a, t, n, r, s, i)));
  }
  collectTypes(e, t) {
    if (Array.isArray(e.enum) || Yn(e.const))
      return;
    const n = e.type;
    Array.isArray(n) ? n.forEach(function(r) {
      return t[r] = !0;
    }) : n && (t[n] = !0);
  }
  addDefaultValueCompletions(e, t, n, r = 0) {
    let s = !1;
    if (Yn(e.default)) {
      let i = e.type, a = e.default;
      for (let l = r; l > 0; l--)
        a = [a], i = "array";
      let o;
      typeof a == "object" ? o = "Default value" : o = a.toString().replace(Zd, '"'), n.add({
        kind: this.getSuggestionKind(i),
        label: o,
        insertText: this.getInsertTextForValue(a, t, i),
        insertTextFormat: ze.Snippet,
        detail: w6("json.suggest.default", "Default value")
      }), s = !0;
    }
    Array.isArray(e.examples) && e.examples.forEach((i) => {
      let a = e.type, o = i;
      for (let l = r; l > 0; l--)
        o = [o], a = "array";
      n.add({
        kind: this.getSuggestionKind(a),
        label: this.getLabelForValue(o),
        insertText: this.getInsertTextForValue(o, t, a),
        insertTextFormat: ze.Snippet
      }), s = !0;
    }), this.collectDefaultSnippets(e, t, n, {
      newLineFirst: !0,
      indentFirstObject: !0,
      shouldIndentWithTab: !0
    }), !s && typeof e.items == "object" && !Array.isArray(e.items) && this.addDefaultValueCompletions(e.items, t, n, r + 1);
  }
  addEnumValueCompletions(e, t, n, r) {
    if (Yn(e.const) && !r && n.add({
      kind: this.getSuggestionKind(e.type),
      label: this.getLabelForValue(e.const),
      insertText: this.getInsertTextForValue(e.const, t, e.type),
      insertTextFormat: ze.Snippet,
      documentation: this.fromMarkup(e.markdownDescription) || e.description
    }), Array.isArray(e.enum))
      for (let s = 0, i = e.enum.length; s < i; s++) {
        const a = e.enum[s];
        let o = this.fromMarkup(e.markdownDescription) || e.description;
        e.markdownEnumDescriptions && s < e.markdownEnumDescriptions.length && this.doesSupportMarkdown() ? o = this.fromMarkup(e.markdownEnumDescriptions[s]) : e.enumDescriptions && s < e.enumDescriptions.length && (o = e.enumDescriptions[s]), n.add({
          kind: this.getSuggestionKind(e.type),
          label: this.getLabelForValue(a),
          insertText: this.getInsertTextForValue(a, t, e.type),
          insertTextFormat: ze.Snippet,
          documentation: o
        });
      }
  }
  getLabelForValue(e) {
    return e === null ? "null" : Array.isArray(e) ? JSON.stringify(e) : "" + e;
  }
  collectDefaultSnippets(e, t, n, r, s = 0) {
    if (Array.isArray(e.defaultSnippets))
      for (const i of e.defaultSnippets) {
        let a = e.type, o = i.body, l = i.label, u, f;
        if (Yn(o)) {
          const c = i.type || e.type;
          if (s === 0 && c === "array") {
            const v = {};
            Object.keys(o).forEach((D, S) => {
              S === 0 && !D.startsWith("-") ? v[`- ${D}`] = o[D] : v[`  ${D}`] = o[D];
            }), o = v;
          }
          const d = Object.keys(n.proposed).filter((v) => n.proposed[v].label === xi);
          if (u = this.getInsertTextForSnippetValue(o, t, r, d), u === "" && o)
            continue;
          l = l || this.getLabelForSnippetValue(o);
        } else if (typeof i.bodyText == "string") {
          let c = "", d = "", v = "";
          for (let D = s; D > 0; D--)
            c = c + v + `[
`, d = d + `
` + v + "]", v += this.indentation, a = "array";
          u = c + v + i.bodyText.split(`
`).join(`
` + v) + d + t, l = l || u, f = u.replace(/[\n]/g, "");
        }
        n.add({
          kind: i.suggestionKind || this.getSuggestionKind(a),
          label: l,
          sortText: i.sortText || i.label,
          documentation: this.fromMarkup(i.markdownDescription) || i.description,
          insertText: u,
          insertTextFormat: ze.Snippet,
          filterText: f
        });
      }
  }
  getInsertTextForSnippetValue(e, t, n, r, s) {
    return qi(e, "", (a) => {
      if (typeof a == "string") {
        if (a[0] === "^")
          return a.substr(1);
        if (a === "true" || a === "false")
          return `"${a}"`;
      }
      return a;
    }, { ...n, indentation: this.indentation, existingProps: r }, s) + t;
  }
  addBooleanValueCompletion(e, t, n) {
    n.add({
      kind: this.getSuggestionKind("boolean"),
      label: e ? "true" : "false",
      insertText: this.getInsertTextForValue(e, t, "boolean"),
      insertTextFormat: ze.Snippet,
      documentation: ""
    });
  }
  addNullValueCompletion(e, t) {
    t.add({
      kind: this.getSuggestionKind("null"),
      label: "null",
      insertText: "null" + e,
      insertTextFormat: ze.Snippet,
      documentation: ""
    });
  }
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  getLabelForSnippetValue(e) {
    return JSON.stringify(e).replace(/\$\{\d+:([^}]+)\}|\$\d+/g, "$1");
  }
  getCustomTagValueCompletions(e) {
    rg(this.customTags).forEach((n) => {
      const r = n.split(" ")[0];
      this.addCustomTagValueCompletion(e, " ", r);
    });
  }
  addCustomTagValueCompletion(e, t, n) {
    e.add({
      kind: this.getSuggestionKind("string"),
      label: n,
      insertText: n + t,
      insertTextFormat: ze.Snippet,
      documentation: ""
    });
  }
  getDocumentationWithMarkdownText(e, t) {
    let n = e;
    return this.doesSupportMarkdown() && (t = t.replace(/\${[0-9]+[:|](.*)}/g, (r, s) => s).replace(/\$([0-9]+)/g, ""), n = this.fromMarkup(`${e}
 \`\`\`
${t}
\`\`\``)), n;
  }
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  getSuggestionKind(e) {
    if (Array.isArray(e)) {
      const t = e;
      e = t.length > 0 ? t[0] : null;
    }
    if (!e)
      return pt.Value;
    switch (e) {
      case "string":
        return pt.Value;
      case "object":
        return pt.Module;
      case "property":
        return pt.Property;
      default:
        return pt.Value;
    }
  }
  getCurrentWord(e, t) {
    let n = t - 1;
    const r = e.getText();
    for (; n >= 0 && ` 	
\r\v":{[,]}`.indexOf(r.charAt(n)) === -1; )
      n--;
    return r.substring(n + 1, t);
  }
  fromMarkup(e) {
    if (e && this.doesSupportMarkdown())
      return {
        kind: hn.Markdown,
        value: e
      };
  }
  doesSupportMarkdown() {
    if (this.supportsMarkdown === void 0) {
      const e = this.clientCapabilities.textDocument && this.clientCapabilities.textDocument.completion;
      this.supportsMarkdown = e && e.completionItem && Array.isArray(e.completionItem.documentationFormat) && e.completionItem.documentationFormat.indexOf(hn.Markdown) !== -1;
    }
    return this.supportsMarkdown;
  }
  findItemAtOffset(e, t, n) {
    for (let r = e.items.length - 1; r >= 0; r--) {
      const s = e.items[r];
      if (De(s) && s.range) {
        if (n > s.range[1])
          return r;
        if (n >= s.range[0])
          return r;
      }
    }
    return 0;
  }
  convertToStringValue(e) {
    let t;
    if (typeof e == "string" ? t = ["on", "off", "true", "false", "yes", "no"].includes(e.toLowerCase()) ? `${this.getQuote()}${e}${this.getQuote()}` : e : t = "" + e, t.length === 0)
      return t;
    if (t === "true" || t === "false" || t === "null" || this.isNumberExp.test(t))
      return `"${t}"`;
    t.indexOf('"') !== -1 && (t = t.replace(Zd, '"'));
    let n = !isNaN(parseInt(t)) || t.charAt(0) === "@";
    if (!n) {
      let r = t.indexOf(":", 0);
      for (; r > 0 && r < t.length; r = t.indexOf(":", r + 1)) {
        if (r === t.length - 1) {
          n = !0;
          break;
        }
        const s = t.charAt(r + 1);
        if (s === "	" || s === " ") {
          n = !0;
          break;
        }
      }
    }
    return n && (t = `"${t}"`), t;
  }
  getQuote() {
    return this.isSingleQuote ? "'" : '"';
  }
  /**
   * simplify `{$1:value}` to `value`
   */
  evaluateTab1Symbol(e) {
    return e.replace(/\$\{1:(.*)\}/, "$1");
  }
  isParentCompletionItem(e) {
    return "parent" in e;
  }
}, S6 = class {
  constructor(e) {
    this.telemetry = e;
  }
  getDefinition(e, t) {
    var n;
    try {
      const r = It.getYamlDocument(e), s = e.offsetAt(t.position), i = Wa(s, r);
      if (i) {
        const [a] = i.getNodeFromPosition(s, new cr(e));
        if (a && $t(a)) {
          const o = a.resolve(i.internalDocument);
          if (o && o.range) {
            const l = ie.create(e.positionAt(o.range[0]), e.positionAt(o.range[2])), u = ie.create(e.positionAt(o.range[0]), e.positionAt(o.range[1]));
            return [rl.create(e.uri, l, u)];
          }
        }
      }
    } catch (r) {
      (n = this.telemetry) == null || n.sendError("yaml.definition.error", r);
    }
  }
};
function E6(e, t) {
  const n = It.getYamlDocument(e);
  return t.map((a) => {
    const o = r(a);
    let l;
    for (const u of o)
      l = ia.create(u, l);
    return l ?? ia.create({ start: a, end: a });
  });
  function r(a) {
    const o = e.offsetAt(a), l = [];
    for (const u of n.documents) {
      let f, c;
      for (u.visit((d) => {
        const v = d.offset + d.length;
        if (v < o || i(v - 1, v) === `
` && v - 1 < o)
          return !0;
        let D = d.offset;
        if (D > o) {
          const S = s(d, a);
          if (!S || S > o)
            return !0;
          D = S;
        }
        return (!f || D >= f.offset) && (f = d, c = D), !0;
      }); f; ) {
        const d = c ?? f.offset, v = f.offset + f.length, D = {
          start: e.positionAt(d),
          end: e.positionAt(v)
        }, S = e.getText(D), x = A6(S), N = d + x.length;
        N >= o && (D.end = e.positionAt(N));
        const k = (y, b) => x.startsWith(y) && x.endsWith(b || y);
        (f.type === "string" && (k("'") || k('"')) || f.type === "object" && k("{", "}") || f.type === "array" && k("[", "]")) && l.push({
          start: e.positionAt(d + 1),
          end: e.positionAt(v - 1)
        }), l.push(D), f = f.parent, c = void 0;
      }
      if (l.length > 0)
        break;
    }
    return l.reverse();
  }
  function s(a, o) {
    var l;
    const u = e.positionAt(a.offset);
    if (u.line === o.line) {
      if (((l = a.parent) == null ? void 0 : l.type) === "array" && i(a.offset - 2, a.offset) === "- ")
        return a.offset - 2;
      if (a.type === "array" || a.type === "object") {
        const f = { line: u.line, character: 0 };
        if (e.getText({ start: f, end: u }).trim().length === 0)
          return e.offsetAt(f);
      }
    }
  }
  function i(a, o) {
    return e.getText({
      start: e.positionAt(a),
      end: e.positionAt(o)
    });
  }
}
function A6(e) {
  return e.endsWith(`\r
`) ? e.substring(0, e.length - 2) : e.endsWith(`
`) ? e.substring(0, e.length - 1) : e;
}
var eu;
(function(e) {
  e[e.SchemaStore = 1] = "SchemaStore", e[e.SchemaAssociation = 2] = "SchemaAssociation", e[e.Settings = 3] = "Settings";
})(eu || (eu = {}));
function x6(e) {
  const t = new J5(e.schemaRequestService, e.workspaceContext), n = new D6(t, e.clientCapabilities, It, e.telemetry), r = new K5(t, e.telemetry), s = new Q5(t, e.telemetry), i = new a6(t, e.telemetry), a = new o6(), o = new h6(e.clientCapabilities), l = new p6(t, e.telemetry), u = new l6(e.telemetry), f = new S6(e.telemetry);
  return {
    configure: (c) => {
      t.clearExternalSchemas(), c.schemas && (t.schemaPriorityMapping = /* @__PURE__ */ new Map(), c.schemas.forEach((d) => {
        const v = d.priority ? d.priority : 0;
        t.addSchemaPriority(d.uri, v), t.registerExternalSchema(d.uri, d.fileMatch, d.schema, d.name, d.description, d.versions);
      })), i.configure(c), r.configure(c), n.configure(c, e.yamlSettings), a.configure(c), o.configure(c);
    },
    registerCustomSchemaProvider: (c) => {
      t.registerCustomSchemaProvider(c);
    },
    findLinks: u.findLinks.bind(u),
    doComplete: n.doComplete.bind(n),
    doValidation: i.doValidation.bind(i),
    doHover: r.doHover.bind(r),
    findDocumentSymbols: s.findDocumentSymbols.bind(s),
    findDocumentSymbols2: s.findHierarchicalDocumentSymbols.bind(s),
    doDefinition: f.getDefinition.bind(f),
    resetSchema: (c) => t.onResourceChange(c),
    doFormat: a.format.bind(a),
    doDocumentOnTypeFormatting: d6,
    addSchema: (c, d) => t.saveSchema(c, d),
    deleteSchema: (c) => t.deleteSchema(c),
    modifySchemaContent: (c) => t.addContent(c),
    deleteSchemaContent: (c) => t.deleteContent(c),
    deleteSchemasWhole: (c) => t.deleteSchemas(c),
    getFoldingRanges: u6,
    getSelectionRanges: E6,
    getCodeAction: (c, d) => o.getCodeAction(c, d),
    getCodeLens: (c) => l.getCodeLens(c),
    resolveCodeLens: (c) => l.resolveCodeLens(c)
  };
}
async function N6(e) {
  const t = await fetch(e);
  if (t.ok)
    return t.text();
  throw new Error(`Schema request failed for ${e}`);
}
var L6 = {
  send() {
  },
  sendError(e, t) {
    console.error("monaco-yaml", e, t);
  },
  sendTrack() {
  }
}, k6 = {
  resolveRelativePath(e, t) {
    return String(new URL(e, t));
  }
};
yb((e, { enableSchemaRequest: t, ...n }) => {
  const r = x6({
    // @ts-expect-error Type definitions are wrong. This may be null.
    schemaRequestService: t ? N6 : null,
    telemetry: L6,
    workspaceContext: k6,
    // Copied from https://github.com/microsoft/vscode-json-languageservice/blob/493010da9dc2cd1cc139d403d4709d97064b17e9/src/jsonLanguageTypes.ts#L325-L335
    // Usage: https://github.com/microsoft/monaco-editor/blob/f6dc0eb8fce67e57f6036f4769d92c1666cdf546/src/language/json/jsonWorker.ts#L38
    clientCapabilities: {
      textDocument: {
        completion: {
          completionItem: {
            commitCharactersSupport: !0,
            documentationFormat: ["markdown", "plaintext"]
          }
        },
        moniker: {}
      }
    }
  }), s = (i) => (a, ...o) => {
    const l = e.getMirrorModels();
    for (const u of l)
      if (String(u.uri) === a)
        return i(Zo.create(a, "yaml", u.version, u.getValue()), ...o);
  };
  return r.configure(n), {
    doValidation: s(
      (i) => r.doValidation(i, !!n.isKubernetes)
    ),
    doComplete: s(
      (i, a) => r.doComplete(i, a, !!n.isKubernetes)
    ),
    doDefinition: s(
      (i, a) => r.doDefinition(i, { position: a, textDocument: i })
    ),
    doDocumentOnTypeFormatting: s(
      (i, a, o, l) => r.doDocumentOnTypeFormatting(i, { ch: o, options: l, position: a, textDocument: i })
    ),
    doHover: s(r.doHover),
    format: s(r.doFormat),
    resetSchema: r.resetSchema,
    findDocumentSymbols: s(r.findDocumentSymbols2),
    findLinks: s(r.findLinks),
    getCodeAction: s(
      (i, a, o) => r.getCodeAction(i, { range: a, textDocument: i, context: o })
    ),
    getFoldingRanges: s(
      (i) => r.getFoldingRanges(i, { lineFoldingOnly: !0 })
    ),
    getSelectionRanges: s(r.getSelectionRanges)
  };
});
