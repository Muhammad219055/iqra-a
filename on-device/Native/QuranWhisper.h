#import <Foundation/Foundation.h>

NS_ASSUME_NONNULL_BEGIN
NS_SWIFT_SENDABLE
@interface QuranWhisperRequest : NSObject
@property(nonatomic, readonly, getter=isCancelled) BOOL cancelled;
- (void)cancel;
@end

NS_SWIFT_SENDABLE
@interface QuranWhisper : NSObject
- (nullable instancetype)initWithModelPath:(NSString *)path error:(NSError **)error;
// Caller supplies mono 16 kHz Float32 PCM, at most 15 seconds; call off the UI thread.
- (nullable NSDictionary<NSString *, id> *)transcribePCM:(NSData *)pcm
    request:(QuranWhisperRequest *)request error:(NSError **)error;
@end
NS_ASSUME_NONNULL_END
