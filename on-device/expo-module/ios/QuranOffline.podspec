Pod::Spec.new do |s|
  s.name = 'QuranOffline'
  s.version = '1.0.0'
  s.summary = 'Phone-local Quran recognition and reciter prompts'
  s.description = s.summary
  s.license = { :type => 'MIT' }
  s.author = 'Quran Tutor'
  s.homepage = 'https://github.com/ggml-org/whisper.cpp'
  s.source = { :path => '.' }
  s.platform = :ios, '16.4'
  s.swift_version = '5.9'
  s.static_framework = true
  s.dependency 'ExpoModulesCore'
  s.source_files = ['QuranOfflineModule.swift', 'Core/*.{swift,h,mm}']
  s.exclude_files = ['Core/OfflineApp.swift', 'Core/Bridge.h']
  s.public_header_files = 'Core/QuranWhisper.h'
  s.vendored_frameworks = 'Whisper.xcframework'
  s.resources = 'Resources/*'
  s.frameworks = 'Accelerate'
  s.libraries = 'c++'
  s.pod_target_xcconfig = {
    'DEFINES_MODULE' => 'YES', 'CLANG_CXX_LANGUAGE_STANDARD' => 'c++17',
    'HEADER_SEARCH_PATHS' => '$(inherited) $(PODS_TARGET_SRCROOT)/Whisper.xcframework/ios-arm64/Headers $(PODS_TARGET_SRCROOT)/Whisper.xcframework/ios-arm64-simulator/Headers'
  }
end
