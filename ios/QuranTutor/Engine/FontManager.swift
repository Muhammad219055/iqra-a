import CoreText
import Foundation
import UIKit

public final class FontManager {
    public static func registerCustomFonts() {
        let fontFiles = [
            ("UthmanicHafs", "ttf"),
            ("AmiriQuran-Regular", "ttf")
        ]

        for (name, ext) in fontFiles {
            if let url = Bundle.main.url(forResource: name, withExtension: ext) {
                var error: Unmanaged<CFError>?
                let success = CTFontManagerRegisterFontsForURL(url as CFURL, .process, &error)
                print("CTFontManagerRegisterFontsForURL for \(name).\(ext): success=\(success)")
                if let err = error?.takeRetainedValue() {
                    print("Font registration error for \(name): \(err)")
                }
            } else {
                print("Font \(name).\(ext) not found in Bundle.main")
            }
        }

        // Verify available font names
        print("=== VERIFYING REGISTERED FONTS ===")
        for family in UIFont.familyNames.sorted() {
            let names = UIFont.fontNames(forFamilyName: family)
            if family.lowercased().contains("hafs") || family.lowercased().contains("amiri") || family.lowercased().contains("uthman") {
                print("Found Font -> Family: '\(family)', PostScript: \(names)")
            }
        }
    }
}
