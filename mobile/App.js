import React, { useState, useEffect, useRef } from 'react';
import { AppState, Text, View } from 'react-native';
import { useFonts } from 'expo-font';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import * as SplashScreen from 'expo-splash-screen';
import MushafReader from './MushafReader';
import nativeTutor from './nativeTutor';

SplashScreen.preventAutoHideAsync().catch(() => {});
SplashScreen.setOptions({ duration: 300, fade: true });

export default function App() {
  const [fontsLoaded, fontError] = useFonts({
    UthmanicHafs: require('./assets/fonts/UthmanicHafs.ttf'),
    SurahNames: require('./assets/fonts/madani/SurahNames.ttf'),
    MadaniFrame: require('./assets/fonts/madani/SurahFrame.ttf'),
    Madani1: require('./assets/fonts/madani/p001.ttf'),
  });
  const [qari, setQari] = useState('mishari');
  const [feedbackMode, setFeedbackMode] = useState('prompt');
  const [memorize, setMemorize] = useState(false);
  const [page, setPage] = useState(1);
  const [engine, setEngine] = useState({ state: 'ready', ayah: 1, cursor: 0, loaded: false, message: 'Tap the mic to begin · on-device' });
  const [revealed, setRevealed] = useState({});
  const [substatus, setSubstatus] = useState('Local tutoring: Al-Fatihah');
  const generation = useRef(0);
  const engineRef = useRef(engine);

  useEffect(() => {
    const subscription = nativeTutor?.addListener('onChange', value => {
      engineRef.current = value;
      setEngine(value);
      if (value.transcript) setSubstatus(`Heard: ${value.transcript}`);
    });
    const appState = AppState.addEventListener('change', state => {
      if (state === 'background') { generation.current += 1; nativeTutor?.stop().catch(() => {}); }
    });
    return () => {
      generation.current += 1;
      subscription?.remove(); appState.remove(); nativeTutor?.stop().catch(() => {});
    };
  }, []);
  useEffect(() => { setRevealed({}); }, [memorize]);

  const reportError = error => {
    setEngine(value => ({ ...value, state: 'ready', message: error.message || 'Could not start local listening' }));
  };
  const onRecord = async () => {
    if (!nativeTutor) { setSubstatus('On-device listening requires the installed iPhone build.'); return; }
    const phase = engineRef.current.state;
    if (phase === 'listening') { await nativeTutor.finish().catch(reportError); return; }
    if (phase !== 'ready') { generation.current += 1; await nativeTutor.stop().catch(reportError); return; }
    if (page !== 1) { setSubstatus('Local tutoring currently covers Al-Fatihah. Return to page 1.'); return; }
    const current = ++generation.current;
    try {
      setEngine(value => ({ ...value, state: 'loading', message: 'Preparing the on-device tutor…' }));
      await nativeTutor.prepare();
      if (current !== generation.current) return;
      await nativeTutor.selectReciter(qari);
      await nativeTutor.setFeedbackMode(feedbackMode);
      if (current !== generation.current) return;
      await nativeTutor.listen();
    } catch (error) { if (current === generation.current) reportError(error); }
  };
  const changePage = async number => {
    if (number === page) return;
    generation.current += 1;
    await nativeTutor?.stop().catch(reportError);
    setPage(number); setRevealed({});
    setSubstatus(number === 1 ? 'Local tutoring: Al-Fatihah' : 'Local tutoring is available on page 1');
  };
  const changeQari = async value => {
    setQari(value);
    generation.current += 1;
    await nativeTutor?.stop().catch(reportError);
  };
  const changeFeedback = async value => {
    setFeedbackMode(value);
    await nativeTutor?.setFeedbackMode(value).catch(reportError);
  };
  const prompt = async next => {
    if (!nativeTutor || page !== 1) { setSubstatus('Bundled reciter prompts currently cover Al-Fatihah.'); return; }
    const current = ++generation.current;
    try {
      await nativeTutor.prepare();
      if (current !== generation.current) return;
      await nativeTutor.selectReciter(qari);
      if (current !== generation.current) return;
      await (next ? nativeTutor.playNextAyah() : nativeTutor.playWord());
    } catch (error) { reportError(error); }
  };
  const onWordPress = word => {
    const id = `${word.surah}:${word.ayah}:${word.word_index_in_ayah}`;
    if (memorize) setRevealed(value => ({ ...value, [id]: !value[id] }));
  };
  const statuses = {};
  if (page === 1 && engine.loaded) {
    for (let word = 1; word <= engine.cursor; word++) statuses[`1:${engine.ayah}:${word}`] = 'matched';
    if (engine.message?.startsWith('Possible')) statuses[`1:${engine.ayah}:${engine.cursor + 1}`] = engine.state === 'prompting' ? 'prompted' : 'mistake';
  }
  if (fontError) return <View style={{ flex: 1, backgroundColor: '#FFF9EF', justifyContent: 'center', padding: 24 }}><Text>Reader fonts could not load. Please reopen the app.</Text></View>;
  if (!fontsLoaded) return <View style={{ flex: 1, backgroundColor: '#FFF9EF' }} />;
  return <SafeAreaProvider>
    <MushafReader pageNumber={page} onPageChange={changePage} statuses={statuses}
      memorize={memorize} onMemorizeChange={setMemorize} revealed={revealed} onWordPress={onWordPress}
      recording={['listening', 'recognizing', 'prompting'].includes(engine.state)}
      connecting={['loading', 'permission'].includes(engine.state)} onRecord={onRecord}
      status={engine.message} substatus={substatus}
      qari={qari} onQariChange={changeQari} feedbackMode={feedbackMode} onFeedbackModeChange={changeFeedback}
      onPlayWord={() => prompt(false)} onPlayNextAyah={() => prompt(true)} />
  </SafeAreaProvider>;
}
