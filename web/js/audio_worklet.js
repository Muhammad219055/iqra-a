/**
 * AudioWorklet Processor for Quran Recitation Ingestion.
 * Captures raw microphone audio, downsamples to 16,000 Hz mono PCM,
 * and emits 16-bit signed integer PCM buffers.
 */

class PCMAudioProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        this.targetSampleRate = 16000;
        this.bufferSize = 1600; // 100ms at 16kHz
        this.pcmBuffer = new Int16Array(this.bufferSize);
        this.bufferIndex = 0;
        this.isMuted = false;

        this.port.onmessage = (event) => {
            if (event.data && event.data.action === "MUTE") {
                this.isMuted = true;
                this.bufferIndex = 0;
            } else if (event.data && event.data.action === "UNMUTE") {
                this.isMuted = false;
                this.bufferIndex = 0;
            }
        };
    }

    process(inputs, outputs, parameters) {
        if (this.isMuted) {
            return true;
        }

        const input = inputs[0];
        if (!input || !input[0]) {
            return true;
        }

        const inputChannel = input[0]; // Mono channel
        const inputSampleRate = currentFrame ? sampleRate : 48000;
        const ratio = inputSampleRate / this.targetSampleRate;

        // Downsample via linear interpolation to 16,000 Hz
        for (let i = 0; i < inputChannel.length; i += ratio) {
            const index = Math.floor(i);
            const nextIndex = Math.min(index + 1, inputChannel.length - 1);
            const fraction = i - index;
            const sample = inputChannel[index] * (1 - fraction) + inputChannel[nextIndex] * fraction;

            // Convert float (-1.0 to 1.0) to 16-bit PCM integer (-32768 to 32767)
            const clamped = Math.max(-1.0, Math.min(1.0, sample));
            const pcmVal = clamped < 0 ? clamped * 0x8000 : clamped * 0x7FFF;

            this.pcmBuffer[this.bufferIndex++] = Math.round(pcmVal);

            if (this.bufferIndex >= this.bufferSize) {
                // Post 100ms chunk of 16-bit PCM bytes
                const chunk = new Int16Array(this.pcmBuffer);
                this.port.postMessage(chunk.buffer, [chunk.buffer]);
                this.pcmBuffer = new Int16Array(this.bufferSize);
                this.bufferIndex = 0;
            }
        }

        return true;
    }
}

registerProcessor("pcm-audio-processor", PCMAudioProcessor);
