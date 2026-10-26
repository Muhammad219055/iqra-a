import XCTest
final class ReaderTests: XCTestCase {
    func capture(_ name: String, _ app: XCUIApplication) {
        let shot = XCTAttachment(screenshot: app.screenshot())
        shot.name = name
        shot.lifetime = .keepAlways
        add(shot)
    }
    func tap(_ element: XCUIElement) {
        XCTAssertEqual(XCTWaiter.wait(for: [XCTNSPredicateExpectation(
            predicate: NSPredicate(format: "hittable == true"), object: element)], timeout: 5), .completed)
        element.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5)).tap()
    }
    func atPage(_ number: Int, _ app: XCUIApplication) -> Bool {
        app.buttons.matching(NSPredicate(format: "label BEGINSWITH %@ AND label ENDSWITH %@", "Choose surah.", ", page \(number)")).firstMatch.waitForExistence(timeout: 10)
    }
    func enterPage(_ value: String, _ app: XCUIApplication) {
        let field = app.textFields["Page number"]
        tap(field)
        let old = field.value as? String ?? ""
        let count = old.allSatisfy(\.isNumber) ? old.count : 0
        field.typeText(String(repeating: XCUIKeyboardKey.delete.rawValue, count: count) + value)
    }
    func testReader() {
        continueAfterFailure = false
        let app = XCUIApplication(bundleIdentifier: "host.exp.Exponent")
        app.activate()
        if app.buttons["Quran Tutor"].waitForExistence(timeout: 3) { tap(app.buttons["Quran Tutor"]) }
        if app.buttons["Close"].exists { tap(app.buttons["Close"]) }
        if !app.buttons["Next page"].exists { app.coordinate(withNormalizedOffset: CGVector(dx: 0.02, dy: 0.5)).tap() }
        XCTAssertTrue(app.buttons["Next page"].waitForExistence(timeout: 60), app.debugDescription)
        if app.buttons["Show Quran text"].exists { tap(app.buttons["Show Quran text"]) }
        tap(app.buttons["Browse surahs or go to a page"])
        XCTAssertTrue(app.textFields["Page number"].waitForExistence(timeout: 5))
        enterPage("1", app)
        tap(app.buttons["Go to page"])
        XCTAssertTrue(atPage(1, app))
        capture("page-001", app)
        XCTAssertFalse(app.buttons["Previous page"].isEnabled)
        tap(app.buttons["Next page"])
        XCTAssertTrue(atPage(2, app))
        capture("page-002", app)
        tap(app.buttons["Next page"])
        XCTAssertTrue(atPage(3, app))
        capture("page-003", app)
        app.swipeLeft()
        XCTAssertTrue(atPage(2, app))
        app.swipeRight()
        XCTAssertTrue(atPage(3, app))
        let pageFrame = app.otherElements["mushaf-page-3"].frame
        app.coordinate(withNormalizedOffset: CGVector(dx: 0.02, dy: 0.5)).tap()
        let controlsHidden = NSPredicate(format: "exists == false")
        expectation(for: controlsHidden, evaluatedWith: app.buttons["Browse surahs or go to a page"])
        waitForExpectations(timeout: 5)
        XCTAssertEqual(app.otherElements["mushaf-page-3"].frame, pageFrame)
        XCTAssertTrue(app.staticTexts["Page 3 of 604"].exists)
        capture("reading-focus", app)
        app.coordinate(withNormalizedOffset: CGVector(dx: 0.02, dy: 0.5)).tap()
        XCTAssertTrue(app.buttons["Browse surahs or go to a page"].waitForExistence(timeout: 5))
        let scrubber = app.sliders["Travel through Quran pages"]
        XCTAssertTrue(scrubber.exists)
        scrubber.adjust(toNormalizedSliderPosition: 0.5)
        XCTAssertTrue(app.buttons.matching(NSPredicate(format: "label BEGINSWITH %@", "Choose surah.")).firstMatch.waitForExistence(timeout: 5))
        capture("page-scrubber", app)
        tap(app.buttons["Browse surahs or go to a page"])
        XCTAssertTrue(app.textFields["Page number"].waitForExistence(timeout: 10))
        let drawer = app.otherElements["quran-drawer"]
        XCTAssertTrue(drawer.exists)
        XCTAssertLessThan(drawer.frame.width, app.frame.width)
        capture("navigation-drawer", app)
        tap(app.descendants(matching: .any).matching(NSPredicate(format: "label == %@", "Juz")).firstMatch)
        XCTAssertTrue(app.buttons["Juz 2, page 22"].waitForExistence(timeout: 5))
        tap(app.buttons["Juz 2, page 22"])
        XCTAssertTrue(atPage(22, app))
        XCTAssertEqual(XCTWaiter.wait(for: [XCTNSPredicateExpectation(
            predicate: NSPredicate(format: "exists == false"), object: drawer)], timeout: 5), .completed)
        tap(app.buttons["Browse surahs or go to a page"])
        XCTAssertTrue(app.textFields["Page number"].waitForExistence(timeout: 5))
        enterPage("605", app)
        tap(app.buttons["Go to page"])
        XCTAssertTrue(app.staticTexts["Enter a page from 1 to 604."].waitForExistence(timeout: 5))
        enterPage("604", app)
        tap(app.buttons["Go to page"])
        XCTAssertTrue(atPage(604, app))
        capture("page-604", app)
        XCTAssertFalse(app.buttons["Next page"].isEnabled)
        tap(app.buttons["Hide words for memorization"])
        let hiddenWords = app.otherElements["mushaf-page-604"].buttons.matching(NSPredicate(format: "label BEGINSWITH %@", "Hidden word"))
        XCTAssertTrue(hiddenWords.firstMatch.waitForExistence(timeout: 5))
        capture("memorize", app)
        let visibleHidden = hiddenWords.allElementsBoundByIndex.filter { $0.isHittable }
        XCTAssertFalse(visibleHidden.isEmpty)
        tap(visibleHidden[0])
        XCTAssertTrue(app.buttons["Show Quran text"].exists)
        XCTAssertEqual(hiddenWords.allElementsBoundByIndex.filter { $0.isHittable }.count, visibleHidden.count - 1)
        tap(app.buttons["Recitation settings"])
        XCTAssertTrue(app.staticTexts["Appearance"].waitForExistence(timeout: 10))
        capture("settings", app)
        tap(app.descendants(matching: .any).matching(NSPredicate(format: "label == %@", "Night")).firstMatch)
        tap(app.buttons["Close"])
        capture("night-reader", app)
    }
    func testAppearance() {
        continueAfterFailure = false
        let app = XCUIApplication(bundleIdentifier: "host.exp.Exponent")
        app.activate()
        if app.buttons["Close"].exists { tap(app.buttons["Close"]) }
        if !app.buttons["Next page"].exists { app.coordinate(withNormalizedOffset: CGVector(dx: 0.02, dy: 0.5)).tap() }
        if app.buttons["Show Quran text"].exists { tap(app.buttons["Show Quran text"]) }
        for appearance in ["Day", "Night"] {
            tap(app.buttons["Recitation settings"])
            let option = app.descendants(matching: .any).matching(NSPredicate(format: "label == %@", appearance)).firstMatch
            XCTAssertTrue(option.waitForExistence(timeout: 5))
            tap(option)
            tap(app.buttons["Close"])
            XCTAssertEqual(XCTWaiter.wait(for: [XCTNSPredicateExpectation(
                predicate: NSPredicate(format: "exists == false"), object: app.buttons["Close"])], timeout: 5), .completed)
            capture("\(appearance.lowercased())-glass-controls", app)
            app.coordinate(withNormalizedOffset: CGVector(dx: 0.02, dy: 0.5)).tap()
            capture("\(appearance.lowercased())-full-screen", app)
            app.coordinate(withNormalizedOffset: CGVector(dx: 0.02, dy: 0.5)).tap()
        }
    }

}
