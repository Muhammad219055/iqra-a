#import "QuranWhisper.h"
#include "whisper.h"
#include <atomic>
#include <cmath>
#include <mutex>
#include <vector>

static void fail(NSError **error, NSInteger code, NSString *message) {
    if (error) *error = [NSError errorWithDomain:@"QuranWhisper" code:code
        userInfo:@{NSLocalizedDescriptionKey: message}];
}

@implementation QuranWhisperRequest {
    std::atomic_bool _cancelled;
}
- (instancetype)init {
    self = [super init];
    if (self) _cancelled.store(false);
    return self;
}
- (BOOL)isCancelled { return _cancelled.load(); }
- (void)cancel { _cancelled.store(true); }
@end

@implementation QuranWhisper {
    whisper_context *_context;
    whisper_vad_context *_vad;
    std::mutex _lock;
}
- (instancetype)initWithModelPath:(NSString *)path error:(NSError **)error {
    self = [super init];
    if (!self) return nil;
    auto params = whisper_context_default_params();
    params.use_gpu = false;
    _context = whisper_init_from_file_with_params(path.fileSystemRepresentation, params);
    if (!_context) {
        fail(error, 1, @"Could not load the bundled Quran model.");
        return nil;
    }
    auto vadParams = whisper_vad_default_context_params();
    vadParams.use_gpu = false;
    vadParams.n_threads = 2;
    NSString *vadPath = [path.stringByDeletingLastPathComponent stringByAppendingPathComponent:@"ggml-silero-v6.2.0.bin"];
    _vad = whisper_vad_init_from_file_with_params(vadPath.fileSystemRepresentation, vadParams);
    if (!_vad) { fail(error, 6, @"Could not load the bundled speech detector."); return nil; }
    return self;
}
- (void)dealloc {
    if (_context) whisper_free(_context);
    if (_vad) whisper_vad_free(_vad);
}
- (NSDictionary *)transcribePCM:(NSData *)pcm request:(QuranWhisperRequest *)request error:(NSError **)error {
    std::unique_lock<std::mutex> guard(_lock, std::try_to_lock);
    if (!guard.owns_lock()) { fail(error, 2, @"Recognition is already running."); return nil; }
    if (request.isCancelled) { fail(error, 4, @"Recognition cancelled."); return nil; }
    size_t count = pcm.length / sizeof(float);
    if (pcm.length % sizeof(float) || count < 1600 || count > 240000) {
        fail(error, 3, @"Expected 0.1–15 seconds of mono 16 kHz Float32 PCM."); return nil;
    }
    std::vector<float> samples(count);
    memcpy(samples.data(), pcm.bytes, pcm.length);
    double energy = 0;
    for (float sample : samples) {
        if (!std::isfinite(sample) || fabsf(sample) > 1.0f) {
            fail(error, 3, @"PCM samples must be finite and between −1 and 1."); return nil;
        }
        energy += sample * sample;
    }
    // Avoid Whisper hallucinations on digital silence; this is not speech detection.
    if (sqrt(energy / count) < 0.0001) return @{@"text": @"", @"seconds": @0};
    if (!whisper_vad_detect_speech(_vad, samples.data(), (int)count)) {
        fail(error, 6, @"Speech detection failed. No correction was made."); return nil;
    }
    auto gate = whisper_vad_default_params();
    gate.threshold = 0.6f;
    gate.min_speech_duration_ms = 250;
    auto segments = whisper_vad_segments_from_probs(_vad, gate);
    if (!segments) { fail(error, 6, @"Speech detection failed."); return nil; }
    bool hasSpeech = whisper_vad_segments_n_segments(segments) > 0;
    whisper_vad_free_segments(segments);
    if (request.isCancelled) { fail(error, 4, @"Recognition cancelled."); return nil; }
    if (!hasSpeech) return @{@"text": @"", @"seconds": @0, @"noSpeech": @YES};
    auto params = whisper_full_default_params(WHISPER_SAMPLING_GREEDY);
    params.language = "ar";
    params.translate = false;
    params.no_context = true;
    params.no_timestamps = true;
    params.print_realtime = false;
    params.print_progress = false;
    params.print_timestamps = false;
    params.print_special = false;
    params.n_threads = (int)MAX(1, MIN(4, (int)NSProcessInfo.processInfo.activeProcessorCount - 2));
    params.temperature = 0;
    // Fine-tuned models can loop ("انهم انهم …") on noisy windows; whisper's entropy check
    // retries just those decodes at a higher temperature instead of returning the loop.
    params.temperature_inc = 0.2f;
    params.entropy_thold = 2.4f;
    params.suppress_nst = true; // no "[music]"-style tokens on breath or room noise
    params.abort_callback = [](void *user) { return (bool)[(__bridge QuranWhisperRequest *)user isCancelled]; };
    params.abort_callback_user_data = (__bridge void *)request;
    CFAbsoluteTime start = CFAbsoluteTimeGetCurrent();
    int status = whisper_full(_context, params, samples.data(), (int)count);
    if (request.isCancelled) { fail(error, 4, @"Recognition cancelled."); return nil; }
    if (status != 0) { fail(error, 5, @"Native recognition failed."); return nil; }
    NSMutableString *text = [NSMutableString string];
    for (int i = 0; i < whisper_full_n_segments(_context); ++i)
        [text appendString:@(whisper_full_get_segment_text(_context, i))];
    return @{@"text": [text stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceAndNewlineCharacterSet],
             @"seconds": @(CFAbsoluteTimeGetCurrent() - start)};
}
@end
