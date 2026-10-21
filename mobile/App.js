import 'react-native-url-polyfill/auto';
import React, { useState, useEffect, useRef } from 'react';
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Switch,
  ActivityIndicator,
  SafeAreaView,
  StatusBar,
  Image,
} from 'react-native';
import { useFonts } from 'expo-font';
import { Audio } from 'expo-av';

const surahData = require('./assets/data/quran_surah_1.json');

const toArabicNumerals = (num) => {
  const arabicDigits = ['٠', '١', '٢', '٣', '٤', '٥', '٦', '٧', '٨', '٩'];
  return String(num).replace(/[0-9]/g, (d) => arabicDigits[d]);
};

// Exact 7-line Medina Mushaf Page 1 structure
const MEDINA_LINES = [
  {
    line: 1,
    wordIds: ['1:1:1', '1:1:2', '1:1:3', '1:1:4'],
    ayahAfter: { '1:1:4': 1 },
  },
  {
    line: 2,
    wordIds: ['1:2:1', '1:2:2', '1:2:3', '1:2:4'],
    ayahAfter: { '1:2:4': 2 },
  },
  {
    line: 3,
    wordIds: ['1:3:1', '1:3:2', '1:4:1', '1:4:2', '1:4:3'],
    ayahAfter: { '1:3:2': 3, '1:4:3': 4 },
  },
  {
    line: 4,
    wordIds: ['1:5:1', '1:5:2', '1:5:3', '1:5:4', '1:6:1'],
    ayahAfter: { '1:5:4': 5 },
  },
  {
    line: 5,
    wordIds: ['1:6:2', '1:6:3', '1:7:1', '1:7:2', '1:7:3'],
    ayahAfter: { '1:6:3': 6 },
  },
  {
    line: 6,
    wordIds: ['1:7:4', '1:7:5', '1:7:6', '1:7:7'],
    ayahAfter: {},
  },
  {
    line: 7,
    wordIds: ['1:7:8', '1:7:9'],
    ayahAfter: { '1:7:9': 7 },
  },
];

const wordMap = {};
surahData.words.forEach((w) => {
  wordMap[`${w.surah}:${w.ayah}:${w.word_index_in_ayah}`] = w;
});

const PAGE_INFO = {
  1: { surahName: 'سُورَة الفَاتِحَة', englishName: 'Al-Fatihah', juz: 1 },
  2: { surahName: 'سُورَة البَقَرَة', englishName: 'Al-Baqarah', juz: 1 },
  3: { surahName: 'سُورَة البَقَرَة', englishName: 'Al-Baqarah', juz: 1 },
  4: { surahName: 'سُورَة البَقَرَة', englishName: 'Al-Baqarah', juz: 1 },
  5: { surahName: 'سُورَة البَقَرَة', englishName: 'Al-Baqarah', juz: 1 },
};

const getPageInfo = (page) => {
  if (PAGE_INFO[page]) return PAGE_INFO[page];
  if (page <= 49) return { surahName: 'سُورَة البَقَرَة', englishName: 'Al-Baqarah', juz: Math.ceil(page / 20) };
  return { surahName: 'المصحف الشريف', englishName: 'Holy Quran', juz: Math.ceil(page / 20) };
};

const getPageImageSource = (page) => {
  if (page === 1) return require('./assets/mushaf_pages/page001.png');
  if (page === 2) return require('./assets/mushaf_pages/page002.png');
  if (page === 3) return require('./assets/mushaf_pages/page003.png');
  const padded = String(page).padStart(3, '0');
  return { uri: `https://files.quran.app/hafs/madani/width_1260/page${padded}.png` };
};

export default function App() {
  const [fontsLoaded] = useFonts({
    'UthmanicHafs': require('./assets/fonts/UthmanicHafs.ttf'),
    'AmiriQuran': require('./assets/fonts/AmiriQuran-Regular.ttf'),
  });

  const [isRecording, setIsRecording] = useState(false);
  const [statusMessage, setStatusMessage] = useState('اضغط على الميكروفون لبدء التسميع');
  const [micStatus, setMicStatus] = useState('جاهز');
  const [serverHost, setServerHost] = useState('192.168.19.137:8000');
  const [selectedQari, setSelectedQari] = useState('mishari');
  const [selectedMode, setSelectedMode] = useState('prompt');
  const [isMemorizeMode, setIsMemorizeMode] = useState(false);
  const [viewMode, setViewMode] = useState('mushaf_text'); // 'mushaf_text' | 'scanned_page'
  const [theme, setTheme] = useState('classic'); // 'classic' | 'dark'
  const [currentPage, setCurrentPage] = useState(1);
  const touchStartXRef = useRef(0);

  const [stats, setStats] = useState({ matched: 0, mistakes: 0, prompts: 0, peeks: 0 });
  const [wordStatuses, setWordStatuses] = useState({});

  const wsRef = useRef(null);
  const recordingRef = useRef(null);
  const promptSoundRef = useRef(null);
  const isPromptingRef = useRef(false);

  useEffect(() => {
    resetStatuses(isMemorizeMode);
    return () => {
      cleanupAudio();
    };
  }, []);

  const resetStatuses = (memorize) => {
    const initial = {};
    surahData.words.forEach((w) => {
      initial[`${w.surah}:${w.ayah}:${w.word_index_in_ayah}`] = memorize ? 'hidden' : 'normal';
    });
    setWordStatuses(initial);
  };

  const cleanupAudio = async () => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    if (recordingRef.current) {
      try {
        await recordingRef.current.stopAndUnloadAsync();
      } catch (e) {}
    }
    if (promptSoundRef.current) {
      try {
        await promptSoundRef.current.unloadAsync();
      } catch (e) {}
    }
  };

  const toggleMemorize = (val) => {
    setIsMemorizeMode(val);
    setWordStatuses((prev) => {
      const next = { ...prev };
      surahData.words.forEach((w) => {
        const id = `${w.surah}:${w.ayah}:${w.word_index_in_ayah}`;
        if (next[id] !== 'matched') {
          next[id] = val ? 'hidden' : 'normal';
        }
      });
      return next;
    });
  };

  const peekWord = (wId) => {
    if (wordStatuses[wId] === 'hidden') {
      setWordStatuses((prev) => ({ ...prev, [wId]: 'normal' }));
      setStats((prev) => ({ ...prev, peeks: prev.peeks + 1 }));
    }
  };

  const goToNextPage = () => {
    if (currentPage < 604) {
      setCurrentPage((p) => p + 1);
    }
  };

  const goToPrevPage = () => {
    if (currentPage > 1) {
      setCurrentPage((p) => p - 1);
    }
  };

  const handleTouchStart = (e) => {
    touchStartXRef.current = e.nativeEvent.pageX;
  };

  const handleTouchEnd = (e) => {
    const endX = e.nativeEvent.pageX;
    const diff = endX - touchStartXRef.current;
    if (diff > 45) {
      // Swiped Right -> Previous page in RTL
      goToPrevPage();
    } else if (diff < -45) {
      // Swiped Left -> Next page in RTL
      goToNextPage();
    }
  };

  const toggleRecording = async () => {
    if (isRecording) {
      await stopReciting();
    } else {
      await startReciting();
    }
  };

  const startReciting = async () => {
    try {
      setStatusMessage('جاري الاتصال بمعلم التلاوة...');
      resetStatuses(isMemorizeMode);
      setStats({ matched: 0, mistakes: 0, prompts: 0, peeks: 0 });

      const perm = await Audio.requestPermissionsAsync();
      if (perm.status !== 'granted') {
        setStatusMessage('يرجى السماح بالوصول للميكروفون');
        return;
      }

      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
        staysActiveInBackground: false,
        shouldDuckAndroid: true,
        playThroughEarpieceAndroid: false,
      });

      const wsUrl = `ws://${serverHost}/ws/recite`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = async () => {
        setIsRecording(true);
        setStatusMessage('يستمع الآن... اتلُ الفاتحة');
        setMicStatus('يستمع...');

        ws.send(JSON.stringify({
          event: 'START_SESSION',
          surah: 1,
          reciter: selectedQari,
          prompt_words: 3,
          mode: selectedMode,
          start_ayah: 1,
        }));

        const recording = new Audio.Recording();
        await recording.prepareToRecordAsync({
          android: {
            extension: '.wav',
            outputFormat: Audio.AndroidOutputFormat.MPEG_4,
            audioEncoder: Audio.AndroidAudioEncoder.AAC,
            sampleRate: 16000,
            numberOfChannels: 1,
            bitRate: 128000,
          },
          ios: {
            extension: '.wav',
            audioQuality: Audio.IOSAudioQuality.HIGH,
            sampleRate: 16000,
            numberOfChannels: 1,
            bitRate: 256000,
            linearPCMBitDepth: 16,
            linearPCMIsBigEndian: false,
            linearPCMIsFloat: false,
          },
          web: {},
        });
        await recording.startAsync();
        recordingRef.current = recording;
      };

      ws.onmessage = async (e) => {
        try {
          const msg = JSON.parse(e.data);
          handleServerMessage(msg);
        } catch (err) {
          console.log('WS error:', err);
        }
      };

      ws.onerror = () => {
        setStatusMessage(`تعذر الاتصال بالخادم (${serverHost})`);
        setIsRecording(false);
        setMicStatus('خطأ');
      };

      ws.onclose = () => {
        setIsRecording(false);
        setMicStatus('جاهز');
      };

    } catch (err) {
      setStatusMessage(`خطأ: ${err.message}`);
      setIsRecording(false);
      setMicStatus('جاهز');
    }
  };

  const stopReciting = async () => {
    setIsRecording(false);
    setStatusMessage('تم إيقاف التسميع');
    setMicStatus('جاهز');
    await cleanupAudio();
  };

  const handleServerMessage = async (msg) => {
    const ev = msg.event;

    if (ev === 'WORD_MATCH') {
      const id = `${msg.surah}:${msg.ayah}:${msg.word}`;
      setWordStatuses((prev) => ({ ...prev, [id]: 'matched' }));
      setStats((prev) => ({ ...prev, matched: prev.matched + 1 }));
      setStatusMessage(`أحسنت: ${msg.text_uthmani}`);

    } else if (ev === 'PAUSE_MIC') {
      isPromptingRef.current = true;
      setMicStatus('المعلم يقرأ');

    } else if (ev === 'PLAY_PROMPT') {
      setStats((prev) => ({ ...prev, prompts: prev.prompts + 1 }));
      const id = `${msg.surah}:${msg.ayah}:${msg.word}`;
      setWordStatuses((prev) => ({ ...prev, [id]: 'prompted' }));
      setStatusMessage(`المعلم يلقنك: ${msg.prompt_text}`);

      try {
        const soundUri = `data:audio/wav;base64,${msg.audio_b64}`;
        const { sound } = await Audio.Sound.createAsync(
          { uri: soundUri },
          { shouldPlay: true }
        );
        promptSoundRef.current = sound;

        sound.setOnPlaybackStatusUpdate(async (status) => {
          if (status.didJustFinish) {
            await sound.unloadAsync();
            setTimeout(() => {
              if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify({ event: 'PROMPT_FINISHED' }));
              }
            }, 150);
          }
        });
      } catch (err) {
        console.log('Audio prompt error:', err);
      }

    } else if (ev === 'RESUME_MIC') {
      isPromptingRef.current = false;
      setMicStatus('يستمع...');
      setStatusMessage('واصل التلاوة بارك الله فيك');

    } else if (ev === 'BUZZER_ALERT' || ev === 'SILENT_HIGHLIGHT') {
      setStats((prev) => ({ ...prev, mistakes: prev.mistakes + 1 }));
      const id = `${msg.surah}:${msg.ayah}:${msg.word}`;
      setWordStatuses((prev) => ({ ...prev, [id]: 'mistake' }));
      setStatusMessage(`انتبه: خطأ عند كلمة ${msg.text_uthmani || ''}`);
    }
  };

  if (!fontsLoaded) {
    return (
      <View style={[styles.fullScreen, styles.bgLight, styles.center]}>
        <ActivityIndicator size="large" color="#C9A050" />
        <Text style={styles.loadingText}>تحميل مصحف المدينة المنورة...</Text>
      </View>
    );
  }

  const isDark = theme === 'dark';
  const pageInfo = getPageInfo(currentPage);

  return (
    <View style={[styles.fullScreen, isDark ? styles.bgDark : styles.bgLight]}>
      <StatusBar barStyle={isDark ? 'light-content' : 'dark-content'} />
      <SafeAreaView style={styles.safeContainer}>

        {/* Top Header Navigation (Matching Reference Image 1) */}
        <View style={[styles.topHeader, isDark ? styles.topHeaderDark : styles.topHeaderLight]}>
          <TouchableOpacity
            style={styles.iconBtn}
            onPress={() => setTheme(isDark ? 'classic' : 'dark')}
          >
            <Text style={styles.iconBtnText}>{isDark ? '☀️' : '🌙'}</Text>
          </TouchableOpacity>

          <View style={styles.topHeaderCenter}>
            <Text style={[styles.headerSurahName, isDark ? styles.goldText : styles.headerSurahLight]}>
              {pageInfo.surahName}
            </Text>
            <Text style={styles.headerSubtext}>
              {pageInfo.englishName} • Juz {pageInfo.juz} • Page {currentPage}
            </Text>
          </View>

          <View style={styles.topHeaderRight}>
            <TouchableOpacity
              style={[styles.modeToggleBtn, viewMode === 'scanned_page' && styles.modeToggleBtnActive]}
              onPress={() => setViewMode(viewMode === 'mushaf_text' ? 'scanned_page' : 'mushaf_text')}
            >
              <Text style={styles.modeToggleText}>
                {viewMode === 'mushaf_text' ? '📖 المصحف' : '✨ تفاعلي'}
              </Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Recitation Status Banner */}
        <View style={styles.statusBannerRow}>
          <View style={[styles.statusPill, isRecording ? styles.statusPillActive : styles.statusPillIdle]}>
            <View style={[styles.statusDot, isRecording && styles.statusDotActive]} />
            <Text style={[styles.statusText, isDark ? styles.textLightSub : styles.textDarkSub]}>
              {statusMessage}
            </Text>
          </View>
        </View>

        <ScrollView
          style={styles.scrollView}
          contentContainerStyle={styles.scrollContent}
          showsVerticalScrollIndicator={false}
        >
          {/* MUSHAF DISPLAY WITH SWIPE GESTURE */}
          <View onTouchStart={handleTouchStart} onTouchEnd={handleTouchEnd}>
            {viewMode === 'scanned_page' || currentPage > 1 ? (
              <View style={[styles.scannedFrame, isDark ? styles.scannedDark : styles.scannedLight]}>
                <Image
                  key={`page-${currentPage}`}
                  source={getPageImageSource(currentPage)}
                  style={styles.scannedImage}
                  resizeMode="contain"
                />
              </View>
            ) : (
              <View style={[styles.mushafPaper, isDark ? styles.mushafPaperDark : styles.mushafPaperLight]}>
                <View style={[styles.outerBorder, isDark ? styles.outerBorderDark : styles.outerBorderLight]}>
                  <View style={[styles.innerBorder, isDark ? styles.innerBorderDark : styles.innerBorderLight]}>

                    {/* Symmetrical Medina Surah Banner */}
                    <View style={[styles.surahBanner, isDark ? styles.surahBannerDark : styles.surahBannerLight]}>
                      <Text style={[styles.bannerCornerTag, isDark ? styles.goldText : styles.bannerTagLight]}>
                        آيَاتُهَا ٧
                      </Text>
                      <Text style={[styles.bannerTitle, isDark ? styles.goldText : styles.bannerTitleLight]}>
                        سُورَةُ الفَاتِحَةِ
                      </Text>
                      <Text style={[styles.bannerCornerTag, isDark ? styles.goldText : styles.bannerTagLight]}>
                        مَكِّيَّةٌ
                      </Text>
                    </View>

                    {/* 7 Canonical Medina Mushaf Lines with RTL & Inline Badges */}
                    <View style={styles.medinaLinesContainer}>
                      {MEDINA_LINES.map((lineDef) => (
                        <View key={lineDef.line} style={styles.medinaLineRow}>
                          {lineDef.wordIds.map((wId) => {
                            const word = wordMap[wId];
                            const status = wordStatuses[wId] || 'normal';
                            const hasAyahMarker = lineDef.ayahAfter[wId];

                            return (
                              <React.Fragment key={wId}>
                                <TouchableOpacity
                                  activeOpacity={0.7}
                                  onPress={() => peekWord(wId)}
                                  style={[
                                    styles.wordTouchable,
                                    status === 'matched' && styles.wordMatchedBg,
                                    status === 'mistake' && styles.wordMistakeBg,
                                    status === 'prompted' && styles.wordPromptedBg,
                                  ]}
                                >
                                  <Text
                                    style={[
                                      styles.quranWordText,
                                      isDark ? styles.quranWordDark : styles.quranWordLight,
                                      status === 'matched' && styles.textMatched,
                                      status === 'mistake' && styles.textMistake,
                                      status === 'prompted' && styles.textPrompted,
                                      status === 'hidden' && styles.textHidden,
                                    ]}
                                  >
                                    {word.text_uthmani}
                                  </Text>
                                </TouchableOpacity>

                                {/* Authentic Inline Ayah Marker */}
                                {hasAyahMarker && (
                                  <View style={[styles.inlineAyahMarker, isDark ? styles.markerDark : styles.markerLight]}>
                                    <Text style={[styles.markerNumberText, isDark ? styles.markerTextDark : styles.markerTextLight]}>
                                      {toArabicNumerals(hasAyahMarker)}
                                    </Text>
                                  </View>
                                )}
                              </React.Fragment>
                            );
                          })}
                        </View>
                      ))}
                    </View>

                  </View>
                </View>
              </View>
            )}
          </View>

          {/* PAGE NAVIGATION BAR (Exact Flip Mechanism from Image 1) */}
          <View style={[styles.pageBar, isDark ? styles.pageBarDark : styles.pageBarLight]}>
            <TouchableOpacity
              onPress={goToPrevPage}
              disabled={currentPage <= 1}
              style={[styles.pageNavBtn, currentPage <= 1 && styles.pageNavBtnDisabled]}
              activeOpacity={0.7}
            >
              <Text style={[styles.pageNavText, currentPage <= 1 && styles.pageNavTextDisabled]}>‹ السابق</Text>
            </TouchableOpacity>

            <View style={styles.pageCenterInfo}>
              <Text style={[styles.pageNumberBadge, isDark ? styles.goldText : styles.pageNumberBadgeLight]}>
                صفحة {toArabicNumerals(currentPage)} من ٦٠٤
              </Text>
              <Text style={styles.pageSwipeHint}>اسحب يميناً أو يساراً لتقليب الصفحة</Text>
            </View>

            <TouchableOpacity
              onPress={goToNextPage}
              disabled={currentPage >= 604}
              style={[styles.pageNavBtn, currentPage >= 604 && styles.pageNavBtnDisabled]}
              activeOpacity={0.7}
            >
              <Text style={[styles.pageNavText, currentPage >= 604 && styles.pageNavTextDisabled]}>التالي ›</Text>
            </TouchableOpacity>
          </View>

          {/* Live Session Stats */}
          <View style={styles.statsContainer}>
            <StatBadge label="صحيح" value={stats.matched} color="#10B981" isDark={isDark} />
            <StatBadge label="أخطاء" value={stats.mistakes} color="#EF4444" isDark={isDark} />
            <StatBadge label="تلقين" value={stats.prompts} color="#3B82F6" isDark={isDark} />
            <StatBadge label="كشف" value={stats.peeks} color="#F59E0B" isDark={isDark} />
          </View>

          {/* Session Settings & Qari Selector */}
          <View style={[styles.controlsCard, isDark ? styles.controlsCardDark : styles.controlsCardLight]}>
            <View style={styles.controlRow}>
              <Text style={[styles.controlLabel, isDark ? styles.textLight : styles.textDark]}>
                القارئ المعلم:
              </Text>
              <View style={styles.btnRow}>
                <TouchableOpacity
                  style={[styles.toggleBtn, selectedQari === 'mishari' && styles.toggleBtnActive]}
                  onPress={() => setSelectedQari('mishari')}
                >
                  <Text style={[styles.toggleBtnText, selectedQari === 'mishari' && styles.toggleBtnTextActive]}>
                    العفاسي
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.toggleBtn, selectedQari === 'husary' && styles.toggleBtnActive]}
                  onPress={() => setSelectedQari('husary')}
                >
                  <Text style={[styles.toggleBtnText, selectedQari === 'husary' && styles.toggleBtnTextActive]}>
                    الحصري
                  </Text>
                </TouchableOpacity>
              </View>
            </View>

            <View style={styles.controlRow}>
              <View>
                <Text style={[styles.controlLabel, isDark ? styles.textLight : styles.textDark]}>
                  وضع التسميع والحفظ:
                </Text>
                <Text style={styles.controlSubLabel}>إخفاء الكلمات حتى تتلوها</Text>
              </View>
              <Switch
                value={isMemorizeMode}
                onValueChange={toggleMemorize}
                trackColor={{ false: '#718096', true: '#C9A050' }}
                thumbColor="#FFFFFF"
              />
            </View>

            <View style={styles.controlRow}>
              <Text style={[styles.controlLabel, isDark ? styles.textLight : styles.textDark]}>
                نوع التنبيه:
              </Text>
              <View style={styles.btnRow}>
                <TouchableOpacity
                  style={[styles.toggleBtnSmall, selectedMode === 'prompt' && styles.toggleBtnActive]}
                  onPress={() => setSelectedMode('prompt')}
                >
                  <Text style={[styles.toggleBtnText, selectedMode === 'prompt' && styles.toggleBtnTextActive]}>
                    صوت المعلم
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.toggleBtnSmall, selectedMode === 'buzzer' && styles.toggleBtnActive]}
                  onPress={() => setSelectedMode('buzzer')}
                >
                  <Text style={[styles.toggleBtnText, selectedMode === 'buzzer' && styles.toggleBtnTextActive]}>
                    جرس
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.toggleBtnSmall, selectedMode === 'silent' && styles.toggleBtnActive]}
                  onPress={() => setSelectedMode('silent')}
                >
                  <Text style={[styles.toggleBtnText, selectedMode === 'silent' && styles.toggleBtnTextActive]}>
                    صامت
                  </Text>
                </TouchableOpacity>
              </View>
            </View>

            <View style={styles.controlRow}>
              <Text style={[styles.controlLabel, isDark ? styles.textLight : styles.textDark]}>
                عنوان الخادم:
              </Text>
              <TextInput
                style={[styles.serverInput, isDark ? styles.serverInputDark : styles.serverInputLight]}
                value={serverHost}
                onChangeText={setServerHost}
                placeholder="192.168.1.X:8000"
                placeholderTextColor="#A0AEC0"
                autoCapitalize="none"
                autoCorrect={false}
              />
            </View>
          </View>

          {/* Big Recite Action Button */}
          <TouchableOpacity
            style={[styles.reciteButton, isRecording ? styles.reciteButtonActive : styles.reciteButtonIdle]}
            onPress={toggleRecording}
            activeOpacity={0.88}
          >
            <Text style={styles.reciteButtonIcon}>
              {isRecording ? '⏹' : '🎙️'}
            </Text>
            <Text style={styles.reciteButtonText}>
              {isRecording ? 'إنهاء التسميع • Stop Reciting' : 'ابدأ التلاوة والتسميع • Start Reciting'}
            </Text>
          </TouchableOpacity>

        </ScrollView>
      </SafeAreaView>
    </View>
  );
}

function StatBadge({ label, value, color, isDark }) {
  return (
    <View style={[styles.statBadge, isDark ? styles.statBadgeDark : styles.statBadgeLight]}>
      <Text style={[styles.statValue, { color }]}>{value}</Text>
      <Text style={[styles.statLabel, isDark ? styles.statLabelDark : styles.statLabelLight]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  fullScreen: {
    flex: 1,
    width: '100%',
    height: '100%',
  },
  safeContainer: {
    flex: 1,
  },
  bgLight: {
    backgroundColor: '#FAF7EE',
  },
  bgDark: {
    backgroundColor: '#0B0F19',
  },
  center: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    fontFamily: 'AmiriQuran',
    fontSize: 18,
    marginTop: 14,
    color: '#8A5D00',
  },
  textLight: {
    color: '#E2E8F0',
  },
  textDark: {
    color: '#1A202C',
  },
  goldText: {
    color: '#D4AF37',
  },
  textLightSub: {
    color: '#94A3B8',
  },
  textDarkSub: {
    color: '#64748B',
  },

  // Top Header Navigation Bar
  topHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  topHeaderLight: {
    backgroundColor: '#FAF7EE',
    borderBottomColor: '#E6DFC8',
  },
  topHeaderDark: {
    backgroundColor: '#0B0F19',
    borderBottomColor: '#1F2937',
  },
  topHeaderCenter: {
    alignItems: 'center',
  },
  topHeaderRight: {
    alignItems: 'flex-end',
  },
  headerSurahName: {
    fontFamily: 'AmiriQuran',
    fontSize: 22,
    fontWeight: 'bold',
  },
  headerSurahLight: {
    color: '#1E293B',
  },
  headerSubtext: {
    fontSize: 11,
    color: '#78716C',
    marginTop: -2,
  },
  iconBtn: {
    padding: 8,
    borderRadius: 8,
    backgroundColor: 'rgba(150, 150, 150, 0.12)',
  },
  iconBtnText: {
    fontSize: 15,
  },
  modeToggleBtn: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    backgroundColor: 'rgba(201, 160, 80, 0.12)',
    borderWidth: 1,
    borderColor: '#C9A050',
  },
  modeToggleBtnActive: {
    backgroundColor: '#C9A050',
  },
  modeToggleText: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#8A5D00',
  },

  // Status Banner Row
  statusBannerRow: {
    paddingHorizontal: 16,
    paddingVertical: 6,
    alignItems: 'center',
  },
  statusPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 16,
  },
  statusPillActive: {
    backgroundColor: 'rgba(16, 185, 129, 0.15)',
  },
  statusPillIdle: {
    backgroundColor: 'rgba(120, 113, 108, 0.12)',
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#78716C',
  },
  statusDotActive: {
    backgroundColor: '#10B981',
  },
  statusText: {
    fontSize: 12,
    fontWeight: '600',
  },

  // Scroll Content
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: 12,
    paddingBottom: 40,
    gap: 12,
  },

  // Scanned Page Frame
  scannedFrame: {
    borderRadius: 14,
    borderWidth: 2,
    overflow: 'hidden',
    height: 520,
    justifyContent: 'center',
    alignItems: 'center',
  },
  scannedLight: {
    backgroundColor: '#FFFFFF',
    borderColor: '#C9A050',
  },
  scannedDark: {
    backgroundColor: '#030712',
    borderColor: '#846322',
  },
  scannedImage: {
    width: '100%',
    height: '100%',
  },

  // Interactive Medina Mushaf Paper
  mushafPaper: {
    borderRadius: 16,
    padding: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.08,
    shadowRadius: 8,
    elevation: 3,
  },
  mushafPaperLight: {
    backgroundColor: '#FDFCFA',
  },
  mushafPaperDark: {
    backgroundColor: '#0F172A',
  },
  outerBorder: {
    borderRadius: 12,
    borderWidth: 2,
    padding: 6,
  },
  outerBorderLight: {
    borderColor: '#C9A050',
  },
  outerBorderDark: {
    borderColor: '#846322',
  },
  innerBorder: {
    borderRadius: 8,
    borderWidth: 1.5,
    paddingVertical: 14,
    paddingHorizontal: 8,
    alignItems: 'center',
  },
  innerBorderLight: {
    borderColor: '#1E657D',
    backgroundColor: '#FAF7EE',
  },
  innerBorderDark: {
    borderColor: '#0284C7',
    backgroundColor: '#0B1120',
  },

  // Surah Header Banner
  surahBanner: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    width: '100%',
    borderRadius: 6,
    borderWidth: 1.5,
    paddingVertical: 5,
    paddingHorizontal: 12,
    marginBottom: 16,
  },
  surahBannerLight: {
    backgroundColor: '#F5EEDB',
    borderColor: '#C9A050',
  },
  surahBannerDark: {
    backgroundColor: '#1E1B15',
    borderColor: '#D4AF37',
  },
  bannerTitle: {
    fontFamily: 'AmiriQuran',
    fontSize: 22,
    textAlign: 'center',
  },
  bannerTitleLight: {
    color: '#8A5D00',
  },
  bannerCornerTag: {
    fontFamily: 'AmiriQuran',
    fontSize: 12,
  },
  bannerTagLight: {
    color: '#9C7829',
  },

  // 7 Medina Lines Container
  medinaLinesContainer: {
    width: '100%',
    gap: 12,
  },
  medinaLineRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    alignItems: 'center',
    direction: 'rtl',
  },
  wordTouchable: {
    paddingHorizontal: 3,
    paddingVertical: 2,
    borderRadius: 4,
    marginHorizontal: 1,
  },
  wordMatchedBg: {
    backgroundColor: 'rgba(16, 185, 129, 0.2)',
  },
  wordMistakeBg: {
    backgroundColor: 'rgba(239, 68, 68, 0.25)',
  },
  wordPromptedBg: {
    backgroundColor: 'rgba(59, 130, 246, 0.25)',
  },
  quranWordText: {
    fontFamily: 'UthmanicHafs',
    fontSize: 22,
    lineHeight: 38,
    writingDirection: 'rtl',
    textAlign: 'center',
  },
  quranWordLight: {
    color: '#1A1714',
  },
  quranWordDark: {
    color: '#F8FAFC',
  },
  textMatched: {
    color: '#059669',
    fontWeight: 'bold',
  },
  textMistake: {
    color: '#DC2626',
    fontWeight: 'bold',
    textDecorationLine: 'underline',
  },
  textPrompted: {
    color: '#2563EB',
    fontWeight: 'bold',
  },
  textHidden: {
    color: 'rgba(150, 150, 150, 0.25)',
    backgroundColor: 'rgba(150, 150, 150, 0.15)',
    borderRadius: 4,
  },

  // Authentic Inline Ayah Marker Medallion
  inlineAyahMarker: {
    width: 26,
    height: 26,
    borderRadius: 13,
    borderWidth: 1.5,
    justifyContent: 'center',
    alignItems: 'center',
    marginHorizontal: 4,
    alignSelf: 'center',
  },
  markerLight: {
    borderColor: '#C9A050',
    backgroundColor: '#FBF8F0',
  },
  markerDark: {
    borderColor: '#EAB308',
    backgroundColor: '#1E293B',
  },
  markerNumberText: {
    fontFamily: 'AmiriQuran',
    fontSize: 12,
    lineHeight: 16,
    textAlign: 'center',
  },
  markerTextLight: {
    color: '#9C7829',
    fontWeight: 'bold',
  },
  markerTextDark: {
    color: '#FDE047',
    fontWeight: 'bold',
  },

  // Page Flipper Bar
  pageBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderRadius: 14,
    borderWidth: 1,
  },
  pageBarLight: {
    backgroundColor: '#FFFFFF',
    borderColor: '#E6DFC8',
  },
  pageBarDark: {
    backgroundColor: '#111827',
    borderColor: '#1F2937',
  },
  pageNavBtn: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 8,
    backgroundColor: 'rgba(201, 160, 80, 0.15)',
    borderWidth: 1,
    borderColor: '#C9A050',
  },
  pageNavBtnDisabled: {
    opacity: 0.35,
    borderColor: '#CBD5E1',
    backgroundColor: 'transparent',
  },
  pageNavText: {
    fontSize: 13,
    fontWeight: 'bold',
    color: '#8A5D00',
  },
  pageNavTextDisabled: {
    color: '#94A3B8',
  },
  pageCenterInfo: {
    alignItems: 'center',
  },
  pageNumberBadge: {
    fontFamily: 'AmiriQuran',
    fontSize: 16,
    fontWeight: 'bold',
  },
  pageNumberBadgeLight: {
    color: '#1E293B',
  },
  pageSwipeHint: {
    fontSize: 10,
    color: '#94A3B8',
    marginTop: 2,
  },

  // Live Stats Row
  statsContainer: {
    flexDirection: 'row',
    gap: 8,
  },
  statBadge: {
    flex: 1,
    borderRadius: 10,
    paddingVertical: 8,
    alignItems: 'center',
    borderWidth: 1,
  },
  statBadgeLight: {
    backgroundColor: '#FFFFFF',
    borderColor: '#E2E8F0',
  },
  statBadgeDark: {
    backgroundColor: '#111827',
    borderColor: '#1F2937',
  },
  statValue: {
    fontSize: 17,
    fontWeight: 'bold',
  },
  statLabel: {
    fontSize: 9,
    fontWeight: '700',
    marginTop: 2,
    letterSpacing: 0.5,
  },
  statLabelLight: {
    color: '#64748B',
  },
  statLabelDark: {
    color: '#94A3B8',
  },

  // Settings Card
  controlsCard: {
    borderRadius: 14,
    padding: 14,
    gap: 12,
    borderWidth: 1,
  },
  controlsCardLight: {
    backgroundColor: '#FFFFFF',
    borderColor: '#E2E8F0',
  },
  controlsCardDark: {
    backgroundColor: '#111827',
    borderColor: '#1F2937',
  },
  controlRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  controlLabel: {
    fontSize: 13,
    fontWeight: '600',
  },
  controlSubLabel: {
    fontSize: 10,
    color: '#94A3B8',
    marginTop: 2,
  },
  btnRow: {
    flexDirection: 'row',
    gap: 6,
  },
  toggleBtn: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
    backgroundColor: 'rgba(100, 116, 139, 0.1)',
  },
  toggleBtnSmall: {
    paddingHorizontal: 8,
    paddingVertical: 6,
    borderRadius: 6,
    backgroundColor: 'rgba(100, 116, 139, 0.1)',
  },
  toggleBtnActive: {
    backgroundColor: '#C9A050',
  },
  toggleBtnText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#64748B',
  },
  toggleBtnTextActive: {
    color: '#FFFFFF',
  },
  serverInput: {
    width: 150,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 6,
    fontSize: 12,
    borderWidth: 1,
    textAlign: 'center',
  },
  serverInputLight: {
    backgroundColor: '#F8FAFC',
    borderColor: '#CBD5E1',
    color: '#0F172A',
  },
  serverInputDark: {
    backgroundColor: '#1E293B',
    borderColor: '#334155',
    color: '#F8FAFC',
  },

  // Recite Button
  reciteButton: {
    borderRadius: 14,
    paddingVertical: 14,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.16,
    shadowRadius: 5,
    elevation: 3,
    marginTop: 2,
  },
  reciteButtonIdle: {
    backgroundColor: '#10B981',
  },
  reciteButtonActive: {
    backgroundColor: '#EF4444',
  },
  reciteButtonIcon: {
    fontSize: 22,
    marginBottom: 2,
  },
  reciteButtonText: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: 'bold',
  },
});
