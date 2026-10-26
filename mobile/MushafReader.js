import React, { createContext, memo, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import {
  AccessibilityInfo, ActivityIndicator, FlatList, KeyboardAvoidingView, Modal,
  Platform, ScrollView, StyleSheet, Text, TextInput,
  StatusBar, View, useColorScheme, useWindowDimensions,
} from 'react-native';
import PagerView from 'react-native-pager-view';
import Slider from '@react-native-community/slider';
import * as SplashScreen from 'expo-splash-screen';
import { GlassView, isLiquidGlassAvailable } from 'expo-glass-effect';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Haptics from 'expo-haptics';
import Animated, { Easing, useAnimatedStyle, useSharedValue, withSpring, withTiming } from 'react-native-reanimated';
import { scheduleOnRN } from 'react-native-worklets';
import { Gesture, GestureDetector, GestureHandlerRootView } from 'react-native-gesture-handler';
import { useFonts } from 'expo-font';
import { SafeAreaProvider, SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
import { Feather } from '@expo/vector-icons';
import pageFonts from './madaniFonts';

export const mushaf = require('./assets/data/madani.json');
const DAY = {
  paper: '#FFF9EF', ink: '#25251F', muted: '#756D60', rule: '#DED5C5',
  gold: '#98764E', accent: '#98764E', accentSoft: '#F0E7D8', white: '#FFFFFF',
  sheet: '#F7F1E6', card: '#FFFFFF', fill: 'rgba(37,37,31,0.07)',
  red: '#A83232', redSoft: '#FBE5DF', blue: '#275E94', blueSoft: '#E3EDF7',
};
const NIGHT = { ...DAY, paper: '#000000', ink: '#FFFFFF', muted: '#AAA49A', rule: '#302B24',
  gold: '#B79B70', accent: '#B79B70', accentSoft: '#2A2318', white: '#000000',
  sheet: '#141311', card: '#211F1B', fill: 'rgba(255,255,255,0.09)',
  red: '#ED9D91', redSoft: '#472C29', blue: '#A6C9E3', blueSoft: '#293B49' };
const ReaderTheme = createContext(null);
const useReaderTheme = () => useContext(ReaderTheme);
const AnimatedSafeAreaView = Animated.createAnimatedComponent(SafeAreaView);
const EASE_PANEL = Easing.bezier(0.32, 0.72, 0, 1);
const arabic = n => String(n).replace(/\d/g, d => '٠١٢٣٤٥٦٧٨٩'[d]);
const wordKey = w => `${w.surah}:${w.ayah}:${w.word_index_in_ayah}`;

function haptic(kind = 'selection') {
  if (!kind) return;
  const result = kind === 'impact' ? Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light) : Haptics.selectionAsync();
  result.catch(() => {});
}

function ControlMaterial() {
  const { C, night } = useReaderTheme();
  return isLiquidGlassAvailable()
    ? <GlassView pointerEvents="none" glassEffectStyle="regular" colorScheme={night ? 'dark' : 'light'} style={StyleSheet.absoluteFill} />
    : <View pointerEvents="none" style={[StyleSheet.absoluteFill, { backgroundColor: C.paper }]} />;
}

function IntentButton({ label, accessibilityLabel, accessibilityRole = 'button', accessibilityState,
  onPress, style, disabled = false, active = false, hapticKind = 'selection', children }) {
  const activate = useCallback(() => { haptic(hapticKind); onPress(); }, [hapticKind, onPress]);
  const pressed = useSharedValue(0);
  const tap = useMemo(() => Gesture.Tap().enabled(!disabled).maxDistance(8).maxDuration(350)
    .onBegin(() => { 'worklet'; pressed.set(1); })
    .onFinalize(() => { 'worklet'; pressed.set(0); })
    .onEnd((_, success) => { 'worklet'; if (success) scheduleOnRN(activate); }), [disabled, activate]);
  const feedback = useAnimatedStyle(() => ({ opacity: disabled ? 0.3 : 1 - pressed.get() * 0.25 }));
  return <GestureDetector gesture={tap}><Animated.View accessible accessibilityRole={accessibilityRole}
    accessibilityLabel={label ?? accessibilityLabel} accessibilityState={{ ...accessibilityState, disabled, selected: active || accessibilityState?.selected }}
    onAccessibilityTap={disabled ? undefined : activate} style={[style, feedback]}>{children}</Animated.View></GestureDetector>;
}

function IconButton({ name, label, onPress, disabled, active, hapticKind = 'selection' }) {
  const { C, s } = useReaderTheme();
  return <IntentButton label={label} disabled={disabled} active={active} hapticKind={hapticKind} onPress={onPress}
    style={[s.iconButton, active && s.iconActive]}>
    <Feather name={name} size={20} color={active ? C.accent : C.ink} />
  </IntentButton>;
}

const EASE_OUT = Easing.bezier(0.23, 1, 0.32, 1);

function PageScrubber({ pageNumber, onSelect, before, after, reducedMotion }) {
  const { C, s } = useReaderTheme();
  const [preview, setPreview] = useState(pageNumber);
  const lastSurah = useRef(mushaf.pages[pageNumber - 1].surah);
  const lastTick = useRef(0);
  const shown = useSharedValue(0);
  const previewPage = value => {
    const number = Math.round(value);
    const surah = mushaf.pages[number - 1].surah;
    if (surah !== lastSurah.current && Date.now() - lastTick.current >= 100) {
      haptic(); lastTick.current = Date.now();
    }
    lastSurah.current = surah;
    setPreview(number);
  };
  const toggle = visible => shown.set(withTiming(visible ? 1 : 0, { duration: reducedMotion ? 0 : visible ? 160 : 120, easing: EASE_OUT }));
  useEffect(() => { setPreview(pageNumber); }, [pageNumber]);
  // Rises 6pt while fading in; reduced motion keeps only the fade.
  const popupStyle = useAnimatedStyle(() => ({ opacity: shown.get(),
    transform: reducedMotion ? [] : [{ translateY: (1 - shown.get()) * 6 }, { scale: 0.96 + shown.get() * 0.04 }] }));
  const chapter = mushaf.chapters[mushaf.pages[preview - 1].surah - 1];
  return <View style={s.scrubber}>
    <Animated.View style={[s.surahPopup, popupStyle]} accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
      <Text allowFontScaling={false} style={s.surahPopupGlyph}>{String.fromCharCode(0xE000 + chapter.id)}</Text>
      <Text style={s.surahPopupMeta} numberOfLines={1}>{chapter.name_simple} · Page {preview}</Text>
    </Animated.View>
    <View style={s.scrubberTrack}>
      {before}
      <Slider accessibilityLabel="Travel through Quran pages" accessibilityValue={{ min: 1, max: 604, now: preview, text: `Page ${preview}, ${chapter.name_simple}` }}
        style={{ flex: 1, height: 36, marginHorizontal: 4 }} minimumValue={1} maximumValue={604} step={1} value={pageNumber} inverted tapToSeek
        minimumTrackTintColor={C.accent} maximumTrackTintColor={C.rule} thumbTintColor={C.accent}
        onSlidingStart={() => { lastSurah.current = mushaf.pages[pageNumber - 1].surah; setPreview(pageNumber); toggle(true); }} onValueChange={previewPage}
        onSlidingComplete={value => { toggle(false); haptic('impact'); onSelect(Math.round(value)); }} />
      {after}
    </View>
  </View>;
}

function Sheet({ visible, title, subtitle, onClose, children, reducedMotion, drawer = false }) {
  const { C, s } = useReaderTheme();
  const [mounted, setMounted] = useState(visible);
  const { width, height } = useWindowDimensions();
  const distance = useSharedValue(drawer ? Math.min(width * 0.88, 420) : height);
  const progress = useSharedValue(0);
  const start = useSharedValue(0);
  const dismissByDrag = useCallback(() => { haptic('impact'); onClose(); }, [onClose]);
  const open = () => { progress.set(withTiming(1, { duration: reducedMotion ? 0 : 260, easing: EASE_PANEL })); };
  useEffect(() => {
    if (visible) { setMounted(true); open(); }
    else progress.set(withTiming(0, { duration: reducedMotion ? 0 : 220, easing: EASE_PANEL }, finished => {
      if (finished) scheduleOnRN(setMounted, false);
    }));
  }, [visible, reducedMotion]);
  const backdropStyle = useAnimatedStyle(() => ({ opacity: progress.get() }));
  const panelStyle = useAnimatedStyle(() => ({ transform: drawer
    ? [{ translateX: -(1 - progress.get()) * distance.get() }]
    : [{ translateY: (1 - progress.get()) * distance.get() }] }));
  const pan = useMemo(() => {
    const gesture = Gesture.Pan();
    if (drawer) gesture.activeOffsetX([-10, 10]).failOffsetY([-16, 16]);
    else gesture.activeOffsetY([-10, 10]).failOffsetX([-16, 16]);
    return gesture.onStart(() => { 'worklet'; start.set(progress.get()); })
      .onUpdate(event => {
        'worklet';
        const translation = drawer ? -event.translationX : event.translationY;
        progress.set(Math.max(0, Math.min(1, start.get() - translation / distance.get())));
      }).onEnd(event => {
        'worklet';
        const velocity = drawer ? -event.velocityX : event.velocityY;
        if (progress.get() < 0.7 || velocity > 650) scheduleOnRN(dismissByDrag);
        else progress.set(withSpring(1, { duration: reducedMotion ? 0 : 300, dampingRatio: 1, overshootClamping: true }));
      });
  }, [drawer, dismissByDrag, reducedMotion]);
  return <Modal visible={mounted} animationType="none" transparent onRequestClose={onClose} onShow={open}>
    <GestureHandlerRootView style={{ flex: 1 }}><SafeAreaProvider>
      <KeyboardAvoidingView style={[s.modalRoot, drawer && s.drawerRoot]} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <Animated.View style={[StyleSheet.absoluteFill, backdropStyle]}>
          <IntentButton style={s.backdrop} onPress={onClose} hapticKind={false} accessibilityLabel="Close panel" accessibilityRole="button" />
        </Animated.View>
        <AnimatedSafeAreaView edges={drawer ? ['top', 'bottom', 'left', 'right'] : ['bottom', 'left', 'right']}
          onLayout={event => { distance.set(drawer ? event.nativeEvent.layout.width : event.nativeEvent.layout.height); }}
          testID={drawer ? 'quran-drawer' : 'recitation-sheet'} style={[s.sheet, drawer && s.drawer, panelStyle]} accessibilityViewIsModal>
          <GestureDetector gesture={pan}><View>
            {!drawer && <View style={s.handle} />}
            <View style={s.sheetHeading}><View style={{ flex: 1 }}><Text style={s.sheetTitle}>{title}</Text>
              {!!subtitle && <Text style={s.sheetSubtitle} numberOfLines={1}>{subtitle}</Text>}</View>
              <IntentButton label="Close" onPress={onClose} style={s.closeButton}><Feather name="x" size={18} color={C.ink} /></IntentButton></View>
          </View></GestureDetector>
          {children}
        </AnimatedSafeAreaView>
      </KeyboardAvoidingView>
    </SafeAreaProvider></GestureHandlerRootView>
  </Modal>;
}

function WordTarget({ word, hidden, style, pageTap, onWordPress, children }) {
  const reveal = useCallback(() => { haptic(); onWordPress(word); }, [word, onWordPress]);
  const tap = useMemo(() => Gesture.Tap().maxDistance(8).maxDuration(300).blocksExternalGesture(pageTap)
    .onEnd((_, success) => { 'worklet'; if (success) scheduleOnRN(reveal); }), [pageTap, reveal]);
  return <GestureDetector gesture={tap}><View accessible accessibilityRole="button"
    accessibilityLabel={hidden ? `Hidden word, ayah ${word.ayah}. Press to reveal.` : word.text_uthmani}
    onAccessibilityTap={reveal} style={style}>{children}</View></GestureDetector>;
}

const Page = memo(function Page({ page, width, height, statuses, memorize, revealed, onWordPress, onToggleChrome }) {
  const { C, s } = useReaderTheme();
  const tap = useMemo(() => Gesture.Tap().maxDistance(8).maxDuration(250)
    .onEnd((_, success) => { 'worklet'; if (success) scheduleOnRN(onToggleChrome); }), [onToggleChrome]);
  const [loaded, error] = useFonts({ [`Madani${page.page}`]: pageFonts[page.page] });
  const innerWidth = Math.min(width - 32, 620);
  const firstLine = Math.min(...page.lines.map(l => l.number));
  const rowCount = Math.max(...page.lines.map(l => l.number)) - firstLine + 1;
  const lineHeight = (height - 16) / Math.max(15, rowCount);
  const maxAdvance = Math.max(...page.lines.map(l => l.words.reduce((sum, w) => sum + w.advance, 0)));
  // One size per page; hmtx advances determine fit, never a character-count estimate.
  const fontSize = Math.min(innerWidth / (maxAdvance + 0.3), lineHeight / 1.62);
  const blockHeight = lineHeight * rowCount;
  if (!loaded) return <View style={[s.page, { width, height }]}>
    {error ? <Text style={s.error}>This page’s font could not be loaded.</Text> : <ActivityIndicator color={C.accent} />}
  </View>;
  return <GestureDetector gesture={tap}><View accessible={false} style={[s.page, { width, height }]} testID={`mushaf-page-${page.page}`}>
    <View style={{ width: innerWidth, height: blockHeight }}>
      {page.lines.map(line => {
        const top = (line.number - firstLine) * lineHeight;
        const frameWidth = Math.min(innerWidth, lineHeight / 0.124);
        const frameHeight = frameWidth * 0.124;
        if (line.type === 'header') return <View key={line.number} style={[s.printLine, s.surahHeader, { top, height: lineHeight, width: innerWidth }]}>
          <Text accessible={false} allowFontScaling={false} style={{ fontFamily: 'MadaniFrame', fontSize: frameWidth, lineHeight: frameHeight, color: C.gold }}>{'\uE000'}</Text>
          <Text accessibilityLabel={mushaf.chapters[line.surah - 1].name_arabic} allowFontScaling={false}
            numberOfLines={1} adjustsFontSizeToFit style={[s.surahName, {
              width: frameWidth * 0.64, height: frameHeight * 0.76,
              fontSize: frameHeight * 0.52, lineHeight: frameHeight * 0.76,
            }]}>{String.fromCharCode(0xE000 + line.surah)}</Text>
        </View>;
        if (line.type === 'bismillah') return <View key={line.number} style={[s.printLine, { top, height: lineHeight, width: innerWidth }]}>
          <Text accessibilityLabel="بسم الله الرحمن الرحيم" allowFontScaling={false}
            style={{ fontFamily: 'Madani1', fontSize: fontSize * 0.85, color: C.ink }}>{'ﱁﱂﱃﱄ'}</Text>
        </View>;
        const advance = line.words.reduce((sum, word) => sum + word.advance * fontSize, 0);
        const gap = line.centered ? 0 : Math.max(0, (innerWidth - advance) / Math.max(1, line.words.length - 1));
        let right = line.centered ? (innerWidth - advance) / 2 : 0;
        return <View key={line.number} style={[s.printLine, { top, height: lineHeight, width: innerWidth }]}>
          {line.words.map(word => {
            const key = wordKey(word);
            const status = statuses[key];
            const hidden = memorize && !word.end && (!status || status === 'hidden' || status === 'normal') && !revealed[key];
            const wordWidth = word.advance * fontSize;
            const position = right;
            right += wordWidth + gap;
            const feedback = status === 'matched' ? { color: C.accent, backgroundColor: C.accentSoft }
              : status === 'mistake' ? { color: C.red, backgroundColor: C.redSoft }
                : status === 'prompted' ? { color: C.blue, backgroundColor: C.blueSoft } : { color: C.ink };
            const glyph = hidden ? null : <Text key={key} accessible={!(memorize && !word.end)}
              accessibilityRole="text" accessibilityLabel={`${word.text_uthmani}${status ? `, ${status}` : ''}`}
              allowFontScaling={false} style={[s.glyph, { right: memorize && !word.end ? 0 : position, width: wordWidth,
                fontFamily: `Madani${page.page}`, fontSize, lineHeight, ...feedback }]}>{word.glyph}</Text>;
            return memorize && !word.end ? <WordTarget key={key} word={word} hidden={hidden} pageTap={tap}
              onWordPress={onWordPress} style={{ position: 'absolute', right: position, width: wordWidth, height: lineHeight }}>
              {glyph}
            </WordTarget> : glyph;
          })}
        </View>;
      })}
    </View>
  </View></GestureDetector>;
});

function Reader({ pageNumber, onPageChange, statuses, memorize, onMemorizeChange,
  revealed, onWordPress, recording, connecting, onRecord, status, substatus,
  qari, onQariChange, feedbackMode, onFeedbackModeChange, onShowIntro, onPlayWord, onPlayNextAyah }) {
  const { C, s, night, setMode } = useReaderTheme();
  const { width: windowWidth, height: windowHeight } = useWindowDimensions();
  const insets = useSafeAreaInsets();
  const reserved = useRef({ top: insets.top, bottom: insets.bottom });
  // Insets only grow within one orientation (status bar toggles must not move the page); rotation starts fresh.
  const orientation = windowWidth > windowHeight ? 'wide' : 'tall';
  if (reserved.current.orientation !== orientation) reserved.current = { orientation, top: insets.top, bottom: insets.bottom };
  reserved.current.top = Math.max(reserved.current.top, insets.top, 36);
  reserved.current.bottom = Math.max(reserved.current.bottom, insets.bottom, 12);
  const width = windowWidth - insets.left - insets.right;
  const [height, setHeight] = useState(0);
  // Facing pages only on a landscape screen wide enough for two iPhone-mini pages; upright stays one page.
  const spread = orientation === 'wide' && width >= 640 && height > 0;
  const per = spread ? 2 : 1;
  const slot = n => Math.floor((n - 1) / per);
  const current = slot(pageNumber);
  const [panel, setPanel] = useState(null);
  const [chromeVisible, setChromeVisible] = useState(false);
  const chrome = useSharedValue(0);
  const chromeStyle = useAnimatedStyle(() => ({ opacity: chrome.get() }));
  const busy = useRef(false);
  const swipePending = useRef(false);
  const [browseMode, setBrowseMode] = useState('surahs');
  const [query, setQuery] = useState('');
  const [pageInput, setPageInput] = useState('');
  const [pageError, setPageError] = useState('');
  const [reducedMotion, setReducedMotion] = useState(false);
  const pager = useRef(null);
  const page = mushaf.pages[pageNumber - 1];
  const chapter = mushaf.chapters[page.surah - 1];
  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReducedMotion);
    const listener = AccessibilityInfo.addEventListener('reduceMotionChanged', setReducedMotion);
    return () => listener.remove();
  }, []);
  useEffect(() => { chrome.set(withTiming(chromeVisible ? 1 : 0, { duration: reducedMotion ? 0 : 140 })); }, [chromeVisible, reducedMotion]);
  function goTo(number) {
    if (!Number.isInteger(number) || number < 1 || number > 604 || (busy.current && !panel)) return;
    if (slot(number) === current) { if (number !== pageNumber) onPageChange(number); }
    else if (reducedMotion || Math.abs(slot(number) - current) > 1) pager.current?.setPageWithoutAnimation(slot(number));
    else pager.current?.setPage(slot(number));
    setPanel(null);
  }
  function jumpToPage() {
    const normalized = pageInput.replace(/[٠-٩]/g, d => '٠١٢٣٤٥٦٧٨٩'.indexOf(d)).trim();
    if (!/^\d+$/.test(normalized) || Number(normalized) < 1 || Number(normalized) > 604) {
      setPageError('Enter a page from 1 to 604.'); return;
    }
    setPageError(''); goTo(Number(normalized));
  }
  const chapters = mushaf.chapters.filter(ch => `${ch.name_simple} ${ch.name_arabic} ${ch.translated_name.name} ${ch.id}`.toLowerCase().includes(query.toLowerCase().trim()));
  const juzs = Array.from({ length: 30 }, (_, i) => ({ id: i + 1,
    page: mushaf.pages.find(p => p.juz === i + 1).page,
  })).filter(juz => `juz ${juz.id} الجزء ${arabic(juz.id)}`.includes(query.toLowerCase().trim()));
  const choose = (items, selected, onSelect) => <View style={s.group}>{items.map(([value, label], i) =>
    <IntentButton key={value} onPress={() => onSelect(value)} accessibilityRole="radio" accessibilityState={{ checked: selected === value }}
      style={[s.row, i > 0 && s.rowDivider]}><Text style={[s.rowText, selected === value && s.rowTextSelected]}>{label}</Text>
      {selected === value && <Feather name="check" color={C.accent} size={18} />}</IntentButton>)}</View>;
  const segmented = (items, selected, onSelect, role = 'radio') => <View style={s.segmented}>{items.map(([value, label]) =>
    <IntentButton key={value} onPress={() => onSelect(value)} accessibilityRole={role}
      accessibilityState={role === 'tab' ? { selected: selected === value } : { checked: selected === value }}
      style={[s.segment, selected === value && s.segmentActive]}>
      <Text style={[s.segmentText, selected === value && s.segmentTextActive]}>{label}</Text></IntentButton>)}</View>;
  return <SafeAreaView edges={['left', 'right']} style={s.root}>
    <StatusBar hidden={!chromeVisible} animated={false} barStyle={night ? 'light-content' : 'dark-content'} />
    <View pointerEvents="none" style={[s.readingMeta, { top: reserved.current.top, opacity: chromeVisible ? 0 : 1 }]}>
      <Text style={[s.printMeta, { width: width * 0.28 }]} numberOfLines={1}>{chapter.name_arabic}</Text>
      <Text style={[s.printMeta, { width: width * 0.28, textAlign: 'right' }]} numberOfLines={1}>الجزء {arabic(page.juz)}</Text>
    </View>
    {(spread ? [current * 2 + 1, current * 2 + 2] : [pageNumber]).map((number, i) =>
      <Text key={number} pointerEvents="none" accessibilityLabel={`Page ${number} of 604`}
        style={[s.printPageNumber, { bottom: Math.max(2, reserved.current.bottom - 26), opacity: chromeVisible ? 0 : 1 },
          spread && (i === 0 ? { left: width / 2 } : { right: width / 2 })]}>{arabic(number)}</Text>)}
    <View style={[s.viewport, { marginTop: reserved.current.top + 30, marginBottom: Math.max(reserved.current.bottom, 26) + 2 }]}
      onAccessibilityEscape={() => setChromeVisible(true)} onLayout={e => setHeight(e.nativeEvent.layout.height)}>
      {height > 0 && <PagerView key={spread ? 'spread' : 'single'} ref={pager} style={{ flex: 1 }} initialPage={current} layoutDirection="rtl"
        offscreenPageLimit={1} overdrag={false} onPageScrollStateChanged={event => {
          const phase = event.nativeEvent.pageScrollState; busy.current = phase === 'dragging';
          if (phase === 'dragging') swipePending.current = true;
          if (phase === 'idle') swipePending.current = false;
        }}
        onPageSelected={event => {
          const position = event.nativeEvent.position;
          const number = position === current ? pageNumber : position * per + 1;
          if (swipePending.current && number !== pageNumber) haptic('impact');
          swipePending.current = false; busy.current = false; onPageChange(number);
        }}>
        {Array.from({ length: 604 / per }, (_, i) => <View key={i} collapsable={false} style={[{ width: '100%', height: '100%' }, spread && s.spread]}>
          {Math.abs(i - current) <= 1 && (spread
            // row-reverse puts the odd page on the right, as in a bound Mushaf.
            ? [...[i * 2 + 1, i * 2 + 2].map(number => <Page key={number} page={mushaf.pages[number - 1]} width={width / 2} height={height} statuses={statuses}
              memorize={memorize} revealed={revealed} onWordPress={onWordPress} onToggleChrome={() => setChromeVisible(visible => !visible)} />),
              <View key="gutter" pointerEvents="none" style={s.gutter} />]
            : <Page page={mushaf.pages[i]} width={width} height={height} statuses={statuses} memorize={memorize} revealed={revealed}
              onWordPress={onWordPress} onToggleChrome={() => setChromeVisible(visible => !visible)} />)}
        </View>)}
      </PagerView>}
    </View>
    <Animated.View pointerEvents={chromeVisible ? 'auto' : 'none'} accessibilityElementsHidden={!chromeVisible}
      importantForAccessibility={chromeVisible ? 'auto' : 'no-hide-descendants'} style={[s.topBar, { paddingTop: reserved.current.top + 4 }, chromeStyle]}>
      <ControlMaterial />
      <IconButton name="menu" label="Browse surahs or go to a page" onPress={() => setPanel('browse')} />
      <IntentButton onPress={() => setPanel('browse')} accessibilityRole="button" accessibilityLabel={`Choose surah. ${chapter.name_simple}, page ${pageNumber}`} style={s.chapterButton}>
        <Text style={s.chapterTitle} numberOfLines={1} adjustsFontSizeToFit minimumFontScale={0.8}>{chapter.name_simple}</Text>
        <Text style={s.chapterMeta}>Juz {page.juz}</Text>
      </IntentButton>
      <IconButton name="sliders" label="Recitation settings" onPress={() => setPanel('settings')} />
    </Animated.View>
    <Animated.View pointerEvents={chromeVisible ? 'auto' : 'none'} accessibilityElementsHidden={!chromeVisible}
      importantForAccessibility={chromeVisible ? 'auto' : 'no-hide-descendants'} style={[s.floatingToolbar, { paddingBottom: reserved.current.bottom + 6 }, chromeStyle]}>
      <ControlMaterial />
      <PageScrubber pageNumber={pageNumber} onSelect={goTo} reducedMotion={reducedMotion}
        before={<IconButton name="chevron-left" hapticKind="impact" label="Next page" disabled={current === slot(604)} onPress={() => goTo(Math.min(604, pageNumber + per))} />}
        after={<IconButton name="chevron-right" hapticKind="impact" label="Previous page" disabled={current === 0} onPress={() => goTo(Math.max(1, pageNumber - per))} />} />
      {(connecting || recording || status !== 'Tap the mic to begin') && <View pointerEvents="none" style={s.sessionStatus}>
        <Text accessibilityLiveRegion="polite" style={s.status}>{status}</Text>
        {!!substatus && <Text style={s.substatus}>{substatus}</Text>}
      </View>}
      <View style={s.toolbarActions}>
        <IntentButton label={memorize ? 'Show Quran text' : 'Hide words for memorization'} active={memorize}
          onPress={() => onMemorizeChange(!memorize)} style={[s.pill, memorize && s.pillActive]}>
          <Feather name={memorize ? 'eye-off' : 'eye'} size={18} color={memorize ? C.accent : C.ink} />
          <Text style={[s.pillText, memorize && { color: C.accent }]}>Memorize</Text>
        </IntentButton>
        <IntentButton hapticKind="impact" accessibilityLabel={connecting ? 'Cancel connection' : recording ? 'Pause recitation' : 'Start recitation'}
          onPress={onRecord} style={[s.pill, s.mic, recording && s.micRecording]}>
          {connecting ? <ActivityIndicator color={C.paper} /> : <Feather name={recording ? 'square' : 'mic'} size={18} color={C.paper} />}
          <Text style={[s.pillText, { color: C.paper }]}>{connecting ? 'Connecting' : recording ? 'Stop' : 'Recite'}</Text>
        </IntentButton>
      </View>
    </Animated.View>
    <Sheet visible={panel === 'browse'} title="The Quran" subtitle={`${chapter.name_simple} · Page ${pageNumber}`} onClose={() => setPanel(null)} reducedMotion={reducedMotion} drawer>
      <View style={s.drawerControls}>
        {segmented([['surahs', 'Surahs'], ['juz', 'Juz']], browseMode, id => { setBrowseMode(id); setQuery(''); }, 'tab')}
        <View style={s.field}><Feather name="search" size={16} color={C.muted} />
          <TextInput accessibilityLabel={browseMode === 'surahs' ? 'Search surahs' : 'Search juz'} style={s.fieldInput}
            placeholder={browseMode === 'surahs' ? 'Search surahs' : 'Search juz'} placeholderTextColor={C.muted} value={query} onChangeText={setQuery} autoCorrect={false} /></View>
        <View style={s.pageJump}><View style={[s.field, { flex: 1 }]}><Feather name="book-open" size={16} color={C.muted} />
          <TextInput accessibilityLabel="Page number" style={s.fieldInput} placeholder="Go to page 1–604" placeholderTextColor={C.muted}
            value={pageInput} onChangeText={setPageInput} keyboardType="number-pad" onSubmitEditing={jumpToPage} /></View>
          <IntentButton label="Go to page" style={s.goButton} onPress={jumpToPage}><Text style={s.goText}>Go</Text></IntentButton></View>
        {!!pageError && <Text accessibilityRole="alert" style={s.fieldError}>{pageError}</Text>}
      </View>
      <FlatList key={browseMode} style={s.chapterList} data={browseMode === 'surahs' ? chapters : juzs} keyExtractor={item => String(item.id)} keyboardShouldPersistTaps="handled"
        ListEmptyComponent={<Text style={s.empty}>No results found.</Text>}
        renderItem={({ item }) => {
          const current = browseMode === 'juz' ? item.id === page.juz : item.id === page.surah;
          if (browseMode === 'juz') return <IntentButton style={[s.listRow, current && s.listRowCurrent]} accessibilityRole="button"
            accessibilityLabel={`Juz ${item.id}, page ${item.page}`} onPress={() => goTo(item.page)}>
            <Text style={[s.listIndex, current && s.listIndexCurrent]}>{item.id}</Text>
            <View style={s.listText}><Text style={s.listTitle}>Juz {item.id}</Text>
              <Text style={s.listDetail}>{mushaf.chapters[mushaf.pages[item.page - 1].surah - 1].name_simple} · Page {item.page}</Text></View>
            <Text style={s.listArabic} numberOfLines={1}>الجزء {arabic(item.id)}</Text>
          </IntentButton>;
          return <IntentButton style={[s.listRow, current && s.listRowCurrent]} accessibilityRole="button" onPress={() => {
            const target = mushaf.pages.find(p => p.lines.some(l => l.words.some(w => w.surah === item.id && w.ayah === 1 && w.word_index_in_ayah === 1))); goTo(target.page);
          }}><Text style={[s.listIndex, current && s.listIndexCurrent]}>{item.id}</Text>
            <View style={s.listText}><Text style={s.listTitle}>{item.name_simple}</Text>
              <Text style={s.listDetail}>{item.translated_name.name} · {item.verses_count} ayahs</Text></View>
            <Text accessibilityLabel={item.name_arabic} allowFontScaling={false} style={s.surahGlyph}>{String.fromCharCode(0xE000 + item.id)}</Text>
          </IntentButton>;
        }} />
    </Sheet>
    <Sheet visible={panel === 'settings'} title="Settings" onClose={() => setPanel(null)} reducedMotion={reducedMotion}>
      <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={s.settingsContent}>
        <Text style={s.fieldLabel}>Appearance</Text>
        {segmented([['day', 'Day'], ['night', 'Night']], night ? 'night' : 'day', setMode)}
        <Text style={s.fieldLabel}>Teacher’s voice</Text>
        {choose([['mishari', 'Mishari Alafasy'], ['husary', 'Mahmoud Al-Husary']], qari, onQariChange)}
        <Text style={s.fieldLabel}>When you need help</Text>
        {choose([['prompt', 'Recite the word for me'], ['buzzer', 'Vibrate'], ['silent', 'Highlight quietly']], feedbackMode, onFeedbackModeChange)}
        <Text style={s.fieldLabel}>Listening</Text>
        <Text style={s.engineNote}>Listening runs entirely on this iPhone. Local tutoring and reciter prompts currently cover Al-Fatihah. Pause within 15 seconds to check each passage. A matching transcript does not verify pronunciation or every repetition.</Text>
        <IntentButton label="Hear next word" style={s.introLink} onPress={() => { setPanel(null); onPlayWord?.(); }}><Text style={s.introLinkText}>Hear next word</Text></IntentButton>
        <IntentButton label="Hear next ayah" style={s.introLink} onPress={() => { setPanel(null); onPlayNextAyah?.(); }}><Text style={s.introLinkText}>Hear next ayah</Text></IntentButton>
        {onShowIntro && <IntentButton label="Show introduction" style={s.introLink} onPress={() => { setPanel(null); onShowIntro(); }}>
          <Text style={s.introLinkText}>Show introduction</Text></IntentButton>}
        <Text style={s.settingsFoot}>Madinah Mushaf · 15 lines · Hafs</Text>
      </ScrollView>
    </Sheet>
  </SafeAreaView>;
}

const makeStyles = C => StyleSheet.create({
  root: { flex: 1, backgroundColor: C.paper },
  topBar: { position: 'absolute', top: 0, left: 0, right: 0, flexDirection: 'row', alignItems: 'center', paddingHorizontal: 8, paddingBottom: 6, overflow: 'hidden', borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: C.rule },
  floatingToolbar: { position: 'absolute', bottom: 0, left: 0, right: 0, paddingHorizontal: 12, paddingTop: 8, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: C.rule },
  iconButton: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center', borderRadius: 22 },
  iconActive: { backgroundColor: C.accentSoft },
  chapterButton: { flex: 1, alignItems: 'center', minHeight: 44, justifyContent: 'center' },
  chapterTitle: { fontSize: 17, fontWeight: '600', color: C.ink },
  chapterMeta: { color: C.muted, fontSize: 12, marginTop: 2 },
  readingMeta: { position: 'absolute', left: 0, right: 0, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 22, height: 28 },
  printPageNumber: { position: 'absolute', left: 0, right: 0, textAlign: 'center', fontSize: 14, lineHeight: 22, color: C.gold },
  printMeta: { fontSize: 14, lineHeight: 26, color: C.gold },
  scrubber: {}, scrubberLabel: { fontSize: 13, fontWeight: '500', color: C.muted, textAlign: 'center', fontVariant: ['tabular-nums'] },
  scrubberTrack: { flexDirection: 'row', alignItems: 'center' },
  surahPopup: { position: 'absolute', bottom: '100%', alignSelf: 'center', marginBottom: 18, alignItems: 'center',
    paddingHorizontal: 18, paddingTop: 6, paddingBottom: 10, borderRadius: 16, backgroundColor: C.card,
    shadowColor: '#000', shadowOpacity: 0.18, shadowRadius: 16, shadowOffset: { width: 0, height: 6 } },
  surahPopupGlyph: { fontFamily: 'SurahNames', fontSize: 40, lineHeight: 50, color: C.gold },
  surahPopupMeta: { fontSize: 13, fontWeight: '500', color: C.muted, fontVariant: ['tabular-nums'] },
  onboarding: { flex: 1, backgroundColor: C.paper },
  skip: { alignSelf: 'flex-end', minHeight: 44, paddingHorizontal: 20, justifyContent: 'center' },
  skipText: { fontSize: 16, color: C.muted, fontWeight: '500' },
  onboardingPage: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 32 },
  onboardingCard: { borderRadius: 18, backgroundColor: C.paper, borderWidth: StyleSheet.hairlineWidth, borderColor: C.rule, overflow: 'hidden',
    shadowColor: '#000', shadowOpacity: 0.12, shadowRadius: 24, shadowOffset: { width: 0, height: 10 } },
  onboardingMark: { width: 88, height: 88, borderRadius: 44, backgroundColor: C.accentSoft, alignItems: 'center', justifyContent: 'center' },
  onboardingTitle: { fontSize: 28, fontWeight: '700', color: C.ink, textAlign: 'center', marginTop: 36, letterSpacing: -0.3 },
  onboardingBody: { fontSize: 17, lineHeight: 25, color: C.muted, textAlign: 'center', marginTop: 12, maxWidth: 340 },
  onboardingFooter: { paddingHorizontal: 24, paddingBottom: 12, gap: 24, alignItems: 'center' },
  dots: { flexDirection: 'row', gap: 6 },
  dot: { height: 6, borderRadius: 3, backgroundColor: C.rule, transitionProperty: ['width', 'backgroundColor'], transitionDuration: 200 },
  dotActive: { width: 20, backgroundColor: C.accent }, dotIdle: { width: 6 },
  primary: { alignSelf: 'stretch', minHeight: 54, borderRadius: 27, backgroundColor: C.accent, alignItems: 'center', justifyContent: 'center' },
  primaryText: { fontSize: 17, fontWeight: '600', color: C.paper },
  introLink: { alignSelf: 'center', minHeight: 44, justifyContent: 'center', marginTop: 12 }, introLinkText: { fontSize: 14, color: C.accent, fontWeight: '500' },
  toolbarActions: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 4, marginTop: 6 },
  pill: { flexDirection: 'row', alignItems: 'center', gap: 8, height: 44, paddingHorizontal: 18, borderRadius: 22, backgroundColor: C.fill },
  pillActive: { backgroundColor: C.accentSoft }, pillText: { fontSize: 15, fontWeight: '600', color: C.ink },
  mic: { backgroundColor: C.accent }, micRecording: { backgroundColor: C.red },
  viewport: { flex: 1 },
  spread: { flexDirection: 'row-reverse' },
  gutter: { position: 'absolute', left: '50%', top: '6%', bottom: '6%', width: StyleSheet.hairlineWidth, backgroundColor: C.rule }, page: { justifyContent: 'center', alignItems: 'center' },
  printLine: { position: 'absolute', justifyContent: 'center', alignItems: 'center' },
  glyph: { position: 'absolute', textAlign: 'center', includeFontPadding: false, color: C.ink },
  surahHeader: { overflow: 'hidden' },
  surahName: { position: 'absolute', fontFamily: 'SurahNames', color: C.ink, textAlign: 'center', backgroundColor: C.paper, includeFontPadding: false },
  sessionStatus: { position: 'absolute', bottom: '100%', left: 16, right: 16, marginBottom: 12, padding: 12, backgroundColor: C.card, borderRadius: 14 },
  status: { fontSize: 14, color: C.ink, fontWeight: '500' }, substatus: { fontSize: 12, color: C.muted },
  modalRoot: { flex: 1, justifyContent: 'flex-end' },
  backdrop: { ...StyleSheet.absoluteFill, backgroundColor: 'rgba(0,0,0,0.4)' },
  sheet: { backgroundColor: C.sheet, maxHeight: '88%', borderTopLeftRadius: 28, borderTopRightRadius: 28, paddingTop: 8 },
  drawerRoot: { justifyContent: 'flex-start', alignItems: 'flex-start' },
  drawer: { width: '86%', maxWidth: 400, height: '100%', maxHeight: '100%', borderTopLeftRadius: 0, borderTopRightRadius: 0, paddingTop: 0 },
  handle: { width: 36, height: 5, borderRadius: 3, backgroundColor: C.rule, alignSelf: 'center' },
  sheetHeading: { flexDirection: 'row', alignItems: 'center', paddingLeft: 20, paddingRight: 12, paddingTop: 10, paddingBottom: 12 },
  sheetTitle: { fontSize: 22, fontWeight: '700', color: C.ink }, sheetSubtitle: { fontSize: 13, color: C.muted, marginTop: 2 },
  closeButton: { width: 32, height: 32, borderRadius: 16, backgroundColor: C.fill, alignItems: 'center', justifyContent: 'center' },
  drawerControls: { paddingHorizontal: 16, gap: 10, paddingBottom: 12 },
  segmented: { flexDirection: 'row', padding: 3, borderRadius: 12, backgroundColor: C.fill },
  segment: { flex: 1, minHeight: 36, borderRadius: 9, alignItems: 'center', justifyContent: 'center' },
  segmentActive: { backgroundColor: C.card },
  segmentText: { fontSize: 14, fontWeight: '500', color: C.muted }, segmentTextActive: { color: C.ink, fontWeight: '600' },
  field: { flexDirection: 'row', alignItems: 'center', gap: 8, minHeight: 44, paddingHorizontal: 12, borderRadius: 12, backgroundColor: C.card },
  fieldInput: { flex: 1, fontSize: 16, color: C.ink, paddingVertical: 10 },
  fieldError: { color: C.red, fontSize: 13, paddingHorizontal: 4 },
  pageJump: { flexDirection: 'row', gap: 8 },
  goButton: { borderRadius: 12, paddingHorizontal: 18, justifyContent: 'center', backgroundColor: C.accent }, goText: { color: C.paper, fontWeight: '600', fontSize: 15 },
  chapterList: { flexGrow: 0 },
  listRow: { flexDirection: 'row', alignItems: 'center', minHeight: 60, paddingHorizontal: 16, gap: 12, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: C.rule },
  listRowCurrent: { backgroundColor: C.accentSoft },
  listIndex: { width: 28, fontSize: 13, color: C.muted, textAlign: 'center', fontVariant: ['tabular-nums'] }, listIndexCurrent: { color: C.accent, fontWeight: '700' },
  listText: { flex: 1, gap: 2 }, listTitle: { color: C.ink, fontSize: 16, fontWeight: '500' }, listDetail: { fontSize: 12, color: C.muted },
  listArabic: { fontSize: 17, color: C.gold }, surahGlyph: { fontFamily: 'SurahNames', fontSize: 30, color: C.gold },
  empty: { padding: 24, color: C.muted, textAlign: 'center' },
  settingsContent: { paddingHorizontal: 16, paddingBottom: 32 },
  fieldLabel: { fontSize: 12, fontWeight: '600', letterSpacing: 0.6, textTransform: 'uppercase', color: C.muted, marginTop: 20, marginBottom: 8, marginLeft: 4 },
  group: { borderRadius: 12, overflow: 'hidden', backgroundColor: C.card },
  row: { minHeight: 48, paddingHorizontal: 16, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  rowDivider: { borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: C.rule },
  rowText: { fontSize: 16, color: C.ink }, rowTextSelected: { fontWeight: '600' },
  engineNote: { fontSize: 13, lineHeight: 18, color: C.muted, marginTop: 8, marginHorizontal: 4 },
  settingsFoot: { textAlign: 'center', fontSize: 12, color: C.muted, marginTop: 28 },
  error: { color: C.red, fontSize: 14, padding: 12, textAlign: 'center' },
});


const INTRO = [
  { title: 'The Madinah Mushaf', body: 'All 604 pages, line for line as printed, drawn from the original Mushaf glyphs.' },
  { title: 'Hide words to memorize', body: 'Turn on Memorize, then press a hidden word to check yourself.' },
  { title: 'A teacher that listens', body: 'Recitation feedback that runs on your phone is on its way. The reader and memorization work offline today.' },
];
// Words of Al-Fatihah 1–3 stay visible so the memorization preview reads as "in progress".
const INTRO_REVEALED = Object.fromEntries(mushaf.pages[0].lines.flatMap(l => l.words)
  .filter(w => w.ayah <= 3).map(w => [wordKey(w), true]));

function Onboarding({ onDone, reducedMotion }) {
  const { C, s } = useReaderTheme();
  const { width, height } = useWindowDimensions();
  const [index, setIndex] = useState(0);
  const pager = useRef(null);
  const enter = useSharedValue(0);
  useEffect(() => { enter.set(withTiming(1, { duration: reducedMotion ? 0 : 420, easing: EASE_OUT })); }, []);
  // First-launch only, so it earns a gentle settle; the pager's own swipe carries every later step.
  const enterStyle = useAnimatedStyle(() => ({ opacity: enter.get(),
    transform: reducedMotion ? [] : [{ translateY: (1 - enter.get()) * 12 }, { scale: 0.97 + enter.get() * 0.03 }] }));
  const cardWidth = Math.min(width - 96, 300);
  const cardHeight = Math.min(cardWidth * 1.45, height * 0.44);
  const last = index === INTRO.length - 1;
  const visual = i => i === 2
    ? <View style={s.onboardingMark}><Feather name="mic" size={34} color={C.accent} /></View>
    : <View style={[s.onboardingCard, { width: cardWidth, height: cardHeight }]}>
      <Page page={mushaf.pages[0]} width={cardWidth} height={cardHeight} statuses={EMPTY_STATUS} memorize={i === 1}
        revealed={INTRO_REVEALED} onWordPress={() => {}} onToggleChrome={() => {}} />
    </View>;
  return <SafeAreaView style={s.onboarding}>
    <StatusBar barStyle={C.paper === '#000000' ? 'light-content' : 'dark-content'} />
    <IntentButton label="Skip introduction" style={[s.skip, last && { opacity: 0 }]} disabled={last} onPress={onDone}>
      <Text style={s.skipText}>Skip</Text>
    </IntentButton>
    <Animated.View style={[{ flex: 1 }, enterStyle]}>
      <PagerView ref={pager} style={{ flex: 1 }} initialPage={0} onPageSelected={e => setIndex(e.nativeEvent.position)}>
        {INTRO.map((item, i) => <View key={item.title} collapsable={false} style={s.onboardingPage}>
          {visual(i)}
          <Text accessibilityRole="header" style={s.onboardingTitle}>{item.title}</Text>
          <Text style={s.onboardingBody}>{item.body}</Text>
        </View>)}
      </PagerView>
    </Animated.View>
    <View style={s.onboardingFooter}>
      <View style={s.dots} accessible accessibilityLabel={`Step ${index + 1} of ${INTRO.length}`}>
        {INTRO.map((item, i) => <Animated.View key={item.title} style={[s.dot, i === index ? s.dotActive : s.dotIdle]} />)}
      </View>
      <IntentButton hapticKind={last ? 'impact' : 'selection'} label={last ? 'Start reading' : 'Continue'} style={s.primary}
        onPress={() => last ? onDone() : pager.current?.setPage(index + 1)}>
        <Text style={s.primaryText}>{last ? 'Start reading' : 'Continue'}</Text>
      </IntentButton>
    </View>
  </SafeAreaView>;
}
const EMPTY_STATUS = {};

export default function MushafReader(props) {
  const scheme = useColorScheme();
  const [mode, updateMode] = useState(null);
  const [introDone, setIntroDone] = useState(null);
  const [reducedMotion, setReducedMotion] = useState(false);
  useEffect(() => {
    let alive = true;
    AsyncStorage.getItem('reader-appearance').then(saved => {
      if (alive && (saved === 'day' || saved === 'night')) updateMode(current => current ?? saved);
    }).catch(() => {});
    AsyncStorage.getItem('onboarding-complete').then(done => { if (alive) setIntroDone(done === 'yes'); })
      .catch(() => { if (alive) setIntroDone(false); });
    AccessibilityInfo.isReduceMotionEnabled().then(value => { if (alive) setReducedMotion(value); });
    return () => { alive = false; };
  }, []);
  useEffect(() => { if (introDone !== null) SplashScreen.hideAsync().catch(() => {}); }, [introDone]);
  const finishIntro = useCallback(() => {
    setIntroDone(true);
    AsyncStorage.setItem('onboarding-complete', 'yes').catch(() => {});
  }, []);
  const night = (mode ?? scheme) === 'night' || (!mode && scheme === 'dark');
  const value = useMemo(() => {
    const C = night ? NIGHT : DAY;
    return { C, s: makeStyles(C), night, setMode: choice => {
      updateMode(choice);
      AsyncStorage.setItem('reader-appearance', choice).catch(() => {});
    } };
  }, [night]);
  if (introDone === null) return <View style={{ flex: 1, backgroundColor: value.C.paper }} />;
  return <ReaderTheme.Provider value={value}><GestureHandlerRootView style={{ flex: 1 }}>
    {introDone ? <Reader {...props} onShowIntro={() => setIntroDone(false)} /> : <Onboarding onDone={finishIntro} reducedMotion={reducedMotion} />}
  </GestureHandlerRootView></ReaderTheme.Provider>;
}
