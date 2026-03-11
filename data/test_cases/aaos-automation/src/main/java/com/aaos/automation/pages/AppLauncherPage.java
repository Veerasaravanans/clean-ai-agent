package com.aaos.automation.pages;

import io.appium.java_client.android.AndroidDriver;
import org.openqa.selenium.By;
import org.openqa.selenium.WebElement;

import java.util.List;

/**
 * App Launcher Page Object for AAOS Car Display
 * Represents the app drawer/launcher showing all applications
 */
public class AppLauncherPage extends BasePage {

    // App launcher locators
    private static final By APPS_GRID = By.id("com.android.car.carlauncher:id/apps_grid");
    private static final By APP_LIST = By.id("com.android.car.carlauncher:id/apps_grid");
    private static final By APP_ICON_TEMPLATE = By.xpath("//*[@text='%s']");
    
    // Common app names
    public static final String APP_SPOTIFY = "Spotify";
    public static final String APP_SETTINGS = "Settings";
    public static final String APP_PHONE = "Phone";
    public static final String APP_SMS = "Messages";
    public static final String APP_RADIO = "Radio";
    public static final String APP_MAPS = "Maps";
    public static final String APP_PLAY_STORE = "Play Store";

    public AppLauncherPage(AndroidDriver driver) {
        super(driver);
    }

    @Override
    public boolean isPageLoaded() {
        return isElementDisplayed(APPS_GRID);
    }

    @Override
    public String getPageIdentifier() {
        return "App Launcher";
    }

    /**
     * Check if app launcher is showing all available apps
     * @param expectedApps list of expected app names
     * @return true if all apps are visible
     */
    public boolean areAppsVisible(String... expectedApps) {
        for (String app : expectedApps) {
            if (!isTextDisplayed(app)) {
                logger.warn("App not found: {}", app);
                return false;
            }
        }
        return true;
    }

    /**
     * Open Spotify application
     * @return SpotifyPage instance
     */
    public SpotifyPage openSpotify() {
        logger.info("Opening Spotify application");
        clickByText(APP_SPOTIFY);
        sleep(2000);
        return new SpotifyPage(driver);
    }

    /**
     * Open Settings application
     * @return SettingsPage instance
     */
    public SettingsPage openSettings() {
        logger.info("Opening Settings application");
        clickByText(APP_SETTINGS);
        sleep(2000);
        return new SettingsPage(driver);
    }

    /**
     * Open Settings by long press (for specific coordinates)
     * @param x x coordinate
     * @param y y coordinate
     * @param durationSeconds press duration in seconds
     * @return SettingsPage instance
     */
    public SettingsPage openSettingsByLongPress(int x, int y, int durationSeconds) {
        logger.info("Opening Settings via long press at ({}, {})", x, y);
        gestureUtils.longPress(x, y, durationSeconds * 1000L);
        sleep(2000);
        return new SettingsPage(driver);
    }

    /**
     * Open Phone application
     * @return PhonePage instance
     */
    public PhonePage openPhone() {
        logger.info("Opening Phone application");
        clickByText(APP_PHONE);
        sleep(2000);
        return new PhonePage(driver);
    }

    /**
     * Open SMS/Messages application
     * @return SmsPage instance
     */
    public SmsPage openSms() {
        logger.info("Opening SMS application");
        // Try different text variations
        if (isTextDisplayed(APP_SMS)) {
            clickByText(APP_SMS);
        } else if (isTextDisplayed("SMS")) {
            clickByText("SMS");
        } else if (isTextDisplayed("Messaging")) {
            clickByText("Messaging");
        }
        sleep(2000);
        return new SmsPage(driver);
    }

    /**
     * Open any app by name
     * @param appName name of the app
     */
    public void openApp(String appName) {
        logger.info("Opening application: {}", appName);
        clickByText(appName);
        sleep(2000);
    }

    /**
     * Get list of all visible app names
     * @return list of app names
     */
    public List<WebElement> getAllVisibleApps() {
        return driver.findElements(By.xpath("//android.widget.TextView"));
    }

    /**
     * Check if specific app is available
     * @param appName app name
     * @return true if app is available
     */
    public boolean isAppAvailable(String appName) {
        return isTextDisplayed(appName);
    }

    /**
     * Scroll to find app
     * @param appName app name
     */
    public void scrollToApp(String appName) {
        logger.info("Scrolling to find app: {}", appName);
        scrollToText(appName);
    }

    /**
     * Swipe to navigate through app launcher
     * @param direction "left" or "right"
     */
    public void swipeAppLauncher(String direction) {
        if ("left".equalsIgnoreCase(direction)) {
            gestureUtils.swipeLeft(GestureUtils.MEDIUM_SWIPE);
        } else {
            gestureUtils.swipeRight(GestureUtils.MEDIUM_SWIPE);
        }
        sleep(500);
    }

    /**
     * Drag and drop app to new position
     * @param appName app to drag
     * @param offsetX horizontal offset
     * @param offsetY vertical offset
     */
    public void dragApp(String appName, int offsetX, int offsetY) {
        logger.info("Dragging app {} by offset ({}, {})", appName, offsetX, offsetY);
        WebElement app = waitUtils.waitForVisibility(By.xpath("//*[@text='" + appName + "']"));
        int startX = app.getLocation().getX() + app.getSize().getWidth() / 2;
        int startY = app.getLocation().getY() + app.getSize().getHeight() / 2;
        gestureUtils.dragByOffset(startX, startY, offsetX, offsetY);
        sleep(500);
    }
}
