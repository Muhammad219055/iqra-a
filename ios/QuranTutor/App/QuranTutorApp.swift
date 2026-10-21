import SwiftUI
import UIKit

@main
struct QuranTutorApp: App {
    init() {
        FontManager.registerCustomFonts()
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}
