const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const babel = require('@babel/core');
const React = require('react');
const quran = require('../assets/data/madani.json');
let haptics = [];
let state = {}, owner = 'Reader', cursor = 0, refs = [], refCursor = 0, theme, saved;
const shared = initial => { let value = initial; return { get: () => value, set: next => { value = next; } }; };
const gesture = () => { const config = {}; const proxy = new Proxy({}, { get: (_, key) => key === 'config' ? config : (...args) => { config[key] = args; return proxy; } }); return proxy; };
const react = { ...React, memo: fn => fn, useContext: () => theme,
  useCallback: fn => fn, useMemo: fn => fn(), useEffect: () => {},
  useState: initial => { const i = `${owner}:${cursor++}`; if (!(i in state)) state[i] = initial;
    return [state[i], next => { state[i] = typeof next === 'function' ? next(state[i]) : next; }]; },
  useRef: initial => { const i = refCursor++; return refs[i] ??= { current: initial }; },
};
const native = new Proxy({ StyleSheet: { create: x => x,
  absoluteFill: { position: 'absolute', top: 0, bottom: 0, left: 0, right: 0 } },
  Platform: { OS: 'ios' }, useColorScheme: () => 'light', useWindowDimensions: () => ({ width: 402, height: 874 }),
}, { get: (x, key) => x[key] || key });
const animation = { View: 'AnimatedView', createAnimatedComponent: () => 'AnimatedSafeAreaView',
  Easing: { bezier: () => null }, useAnimatedStyle: fn => fn(), useSharedValue: shared,
  withTiming: x => x, withSpring: x => x,
  interpolate: (v, [a, b], [c, d]) => c + (v - a) / (b - a) * (d - c) };
const filename = require('node:path').join(__dirname, '../MushafReader.js');
const code = babel.transformSync(fs.readFileSync(filename, 'utf8'), {
  filename, presets: [['babel-preset-expo', { worklets: false, reanimated: false }]], plugins: ['@babel/plugin-transform-modules-commonjs'],
}).code;
const mod = { exports: {} };
vm.runInNewContext(code + '\nexports.Reader=Reader; exports.Page=Page; exports.DAY=DAY; exports.NIGHT=NIGHT; exports.makeStyles=makeStyles;', {
  module: mod, exports: mod.exports, require: name => {
    if (name === 'react') return react;
    if (name === 'react-native') return native;
    if (name === 'expo-haptics') return { selectionAsync: () => { haptics.push('selection'); return Promise.resolve(); }, impactAsync: () => { haptics.push('impact'); return Promise.resolve(); }, ImpactFeedbackStyle: { Light: 'light' } };
    if (name === 'expo-glass-effect') return { GlassView: 'GlassView', isLiquidGlassAvailable: () => true };
    if (name === '@react-native-community/slider') return 'Slider';
    if (name === 'react-native-pager-view') return 'PagerView';
    if (name === 'expo-splash-screen') return { hideAsync: () => Promise.resolve() };
    if (name === 'react-native-reanimated') return { ...animation, default: animation, __esModule: true };
    if (name === 'react-native-worklets') return { scheduleOnRN: (fn, ...args) => fn(...args) };
    if (name === 'react-native-gesture-handler') return { Gesture: { Tap: gesture, Pan: gesture }, GestureDetector: 'GestureDetector', GestureHandlerRootView: 'GestureRoot' };
    if (name === '@react-native-async-storage/async-storage') return { setItem: (key, value) => { saved = [key, value]; return Promise.resolve(); } };
    if (name === 'react-native-safe-area-context') return { SafeAreaView: 'SafeAreaView', SafeAreaProvider: 'SafeAreaProvider', useSafeAreaInsets: () => ({ left: 0, right: 0, top: 62, bottom: 34 }) };
    if (name === 'expo-font') return { useFonts: () => [true, null] };
    if (name === '@expo/vector-icons') return { Feather: 'Feather' };
    if (name === './madaniFonts') return {};
    if (name === './assets/data/madani.json') return quran;
    return require(name);
  },
});
const { Reader, Page, DAY, NIGHT, makeStyles } = mod.exports;
theme = { C: DAY, s: makeStyles(DAY), night: false, setMode: () => {} };
function nodes(tree) {
  if (!tree || typeof tree !== 'object') return [];
  if (Array.isArray(tree)) return tree.flatMap(nodes);
  if (typeof tree.type === 'function') {
    if (tree.type.name === 'Sheet' && !tree.props.visible) return [];
    // Hook state is keyed per component so nested components cannot steal each other's slots.
    const saved = [owner, cursor]; owner = tree.type.name; cursor = 0;
    try { return nodes(tree.type(tree.props)); } finally { [owner, cursor] = saved; }
  }
  return [tree, ...nodes(tree.props?.children)];
}
const byLabel = (tree, label) => nodes(tree).find(n => n.props.accessibilityLabel === label);
const noop = () => {};
let selected;
const props = { pageNumber: 3, statuses: {}, memorize: false, revealed: {}, onWordPress: noop,
  onPageChange: page => { selected = page; }, onMemorizeChange: noop, onRecord: noop,
  onServerHostChange: noop, onQariChange: noop, onFeedbackModeChange: noop, status: 'Ready' };
function render() { owner = 'Reader'; cursor = 0; refCursor = 0; return Reader(props); }
state = { 'Reader:0': 700 };
let root = render();
let pager = nodes(root).find(n => n.type === 'PagerView');
assert.equal(pager.props.layoutDirection, 'rtl');
assert.equal(pager.props.offscreenPageLimit, 1);
assert.equal(nodes(root).filter(n => n.props.testID?.startsWith('mushaf-page-')).length, 3);
assert.equal(byLabel(root, 'Page 3 of 604').props.children, '٣');
const controls = nodes(root).filter(n => n.type === 'AnimatedView' && n.props.pointerEvents);
assert(controls.every(n => n.props.pointerEvents === 'none' && n.props.style[0].position === 'absolute'));
const scrubber = nodes(root).find(n => n.type === 'Slider');
assert.equal(scrubber.props.minimumValue, 1); assert.equal(scrubber.props.maximumValue, 604);
assert.equal(scrubber.props.inverted, true);
scrubber.props.onSlidingStart();
scrubber.props.onValueChange(304);
assert.equal(selected, undefined, 'Scrubbing must not turn pages before release');
let moved;
pager.props.ref.current = { setPage: index => { moved = index; }, setPageWithoutAnimation: index => { moved = index; } };
scrubber.props.onSlidingComplete(304);
assert.equal(moved, 303); assert(haptics.includes('impact'));
assert.equal(selected, undefined);
byLabel(root, 'Next page').props.onAccessibilityTap();
assert.equal(moved, 3);
assert.equal(selected, undefined, 'Selection must wait for the native page to settle');
pager.props.onPageSelected({ nativeEvent: { position: 3 } });
assert.equal(selected, 4);
pager.props.onPageScrollStateChanged({ nativeEvent: { pageScrollState: 'dragging' } });
moved = null;
byLabel(root, 'Next page').props.onAccessibilityTap();
assert.equal(moved, null, 'Button must not interrupt a native drag');
pager.props.onPageScrollStateChanged({ nativeEvent: { pageScrollState: 'idle' } });

let peeks = 0, toggles = 0;
const pageProps = { page: quran.pages[2], width: 402, height: 700, statuses: {}, memorize: true,
  revealed: {}, onWordPress: () => peeks++, onToggleChrome: () => toggles++ };
let page = Page(pageProps);
const hidden = nodes(page).filter(n => n.props.accessibilityLabel?.startsWith('Hidden word'));
const words = quran.pages[2].lines.flatMap(l => l.words);
assert.equal(hidden.length, words.filter(w => !w.end).length);
assert(hidden.every(n => !n.props.children && !n.props.onPress));
const wordGesture = nodes(page).find(n => n.type === 'GestureDetector' && n.props.gesture.config.blocksExternalGesture);
assert.equal(wordGesture.props.gesture.config.maxDistance[0], 8);
wordGesture.props.gesture.config.onEnd[0]({}, true);
assert.equal(peeks, 1); assert.equal(toggles, 0); assert(haptics.includes('selection'));
const plain = nodes(Page({ ...pageProps, memorize: false }));
assert(plain.filter(n => n.type === 'Text').every(n => !n.props.onPress && !n.props.onLongPress));
const tapGesture = page.props.gesture;
assert.equal(tapGesture.config.maxDistance[0], 8); assert.equal(tapGesture.config.maxDuration[0], 250);
tapGesture.config.onEnd[0]({}, true); assert.equal(toggles, 1);
const visiblePage = nodes(root).find(n => n.props.testID === 'mushaf-page-3');
// A page tap changes overlay state, never the measured reader viewport.
const pageElement = pager.props.children[2].props.children;
pageElement.props.onToggleChrome(); root = render();
assert(nodes(root).filter(n => n.type === 'AnimatedView' && n.props.pointerEvents).every(n => n.props.pointerEvents === 'auto'));
assert.equal(nodes(root).find(n => n.props.testID === 'mushaf-page-3').props.style[1].height, 700);
byLabel(root, 'Browse surahs or go to a page').props.onAccessibilityTap(); root = render();
assert(nodes(root).some(n => n.props.testID === 'quran-drawer'));
assert(nodes(root).filter(n => n.type === 'Modal').every(n => n.props.animationType === 'none'));
const backdrop = byLabel(root, 'Close panel');
byLabel(root, 'Page number').props.onChangeText('605'); root = render();
byLabel(root, 'Go to page').props.onAccessibilityTap(); root = render();
assert(nodes(root).some(n => n.props.children === 'Enter a page from 1 to 604.'));
byLabel(root, 'Page number').props.onChangeText('604'); root = render();
byLabel(root, 'Go to page').props.onAccessibilityTap();
assert.equal(moved, 603, 'Valid page entry must command the native pager');

assert.equal(backdrop.props.style[0].position, 'absolute');
assert.equal(DAY.accent, DAY.gold); assert.equal(NIGHT.accent, NIGHT.gold);
assert.equal(NIGHT.paper, '#000000'); assert.equal(NIGHT.ink, '#FFFFFF'); assert.notEqual(NIGHT.ink, DAY.ink);
state = { 'MushafReader:1': true }; owner = 'MushafReader'; cursor = 0; refCursor = 0;
const wrapper = mod.exports.default(props);
wrapper.props.value.setMode('night');
assert.equal(saved[0], 'reader-appearance'); assert.equal(saved[1], 'night');
// Wide window (landscape / unfolded Duo): facing pages, odd page on the right, buttons step a spread.
native.useWindowDimensions = () => ({ width: 874, height: 402 });
state = { 'Reader:0': 340 }; refs = []; moved = undefined;
root = render();
pager = nodes(root).find(n => n.type === 'PagerView');
assert.equal(pager.key, 'spread'); assert.equal(pager.props.children.length, 302); assert.equal(pager.props.initialPage, 1);
const facing = pager.props.children[1].props.children.filter(n => n.props.page).map(n => n.props.page.page);
assert.equal(facing.join(), '3,4'); assert.equal(pager.props.children[1].props.style[1].flexDirection, 'row-reverse');
pager.props.ref.current = { setPage: index => { moved = index; }, setPageWithoutAnimation: index => { moved = index; } };
byLabel(root, 'Next page').props.onAccessibilityTap();
assert.equal(moved, 2, 'Next must turn a whole spread');
console.log('PASS: native paging settlement/drag guard, fixed overlay geometry, full-screen page number, intentional quick-press glyph reveal, movement threshold, independent panels, and saved night mode, facing-page spreads.');
