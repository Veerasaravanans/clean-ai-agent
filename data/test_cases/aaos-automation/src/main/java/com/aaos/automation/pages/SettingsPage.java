package com.aaos.automation.pages;

import io.appium.java_client.android.AndroidDriver;
import org.openqa.selenium.By;

/**
 * Settings Page Object for AAOS Car Display
 * Represents the system settings application
 */
public class SettingsPage extends BasePage {

    // Settings locators
    private static final By SETTINGS_CONTAINER = By.id("com.android.car.settings:id/fragment_container");
    private static final By SETTINGS_TITLE = By.xpath("//*[@text='Settings']");
    
    // Settings menu items
    private static final String BLUETOOTH = "Bluetooth";
    private static final String NETWORK = "Network";
    private static final String NOTIFICATIONS = "Notifications";
    private static final String SOUND = "Sound";
    private static final String DISPLAY = "Display";
    private static final String APPS = "Apps";
    private static final String SYSTEM = "System";
    private static final String PRIVACY = "Privacy";
    private static final String ACCOUNTS = "Accounts";

    public SettingsPage(AndroidDriver driver) {
        super(driver);
    }

    @Override
    public boolean isPageLoaded() {
        return isElementDisplayed(SETTINGS_CONTAINER) || isTextDisplayed("Settings");
    }

    @Override
    public String getPageIdentifier() {
        return "Settings";
    }

    /**
     * Navigate to Bluetooth settings
     * @return BluetoothSettingsPage instance
     */
    public BluetoothSettingsPage openBluetooth() {
        logger.info("Opening Bluetooth settings");
        clickByText(BLUETOOTH);
        sleep(1500);
        return new BluetoothSettingsPage(driver);
    }

    /**
     * Navigate to Network settings
     * @return SettingsPage (current page)
     */
    public SettingsPage openNetwork() {
        logger.info("Opening Network settings");
        clickByText(NETWORK);
        sleep(1500);
        return this;
    }

    /**
     * Navigate to Notifications settings
     * @return SettingsPage (current page)
     */
    public SettingsPage openNotifications() {
        logger.info("Opening Notifications settings");
        clickByText(NOTIFICATIONS);
        sleep(1500);
        return this;
    }

    /**
     * Navigate to Sound settings
     * @return SettingsPage (current page)
     */
    public SettingsPage openSound() {
        logger.info("Opening Sound settings");
        clickByText(SOUND);
        sleep(1500);
        return this;
    }

    /**
     * Navigate to Display settings
     * @return SettingsPage (current page)
     */
    public SettingsPage openDisplay() {
        logger.info("Opening Display settings");
        clickByText(DISPLAY);
        sleep(1500);
        return this;
    }

    /**
     * Navigate to Apps settings
     * @return SettingsPage (current page)
     */
    public SettingsPage openApps() {
        logger.info("Opening Apps settings");
        clickByText(APPS);
        sleep(1500);
        return this;
    }

    /**
     * Navigate to System settings
     * @return SettingsPage (current page)
     */
    public SettingsPage openSystem() {
        logger.info("Opening System settings");
        clickByText(SYSTEM);
        sleep(1500);
        return this;
    }

    /**
     * Check if Bluetooth option is visible
     * @return true if visible
     */
    public boolean isBluetoothVisible() {
        return isTextDisplayed(BLUETOOTH);
    }

    /**
     * Check if Network option is visible
     * @return true if visible
     */
    public boolean isNetworkVisible() {
        return isTextDisplayed(NETWORK);
    }

    /**
     * Check if Notifications option is visible
     * @return true if visible
     */
    public boolean isNotificationsVisible() {
        return isTextDisplayed(NOTIFICATIONS);
    }

    /**
     * Check if Sound option is visible
     * @return true if visible
     */
    public boolean isSoundVisible() {
        return isTextDisplayed(SOUND);
    }

    /**
     * Check if Display option is visible
     * @return true if visible
     */
    public boolean isDisplayVisible() {
        return isTextDisplayed(DISPLAY);
    }

    /**
     * Navigate to specific settings menu by swipe
     * @param swipeCommand swipe command string
     * @return BluetoothSettingsPage if swiped to Bluetooth
     */
    public BluetoothSettingsPage navigateBySwipe(String swipeCommand) {
        logger.info("Navigating settings by swipe: {}", swipeCommand);
        gestureUtils.executeSwipeCommand(swipeCommand);
        sleep(1500);
        return new BluetoothSettingsPage(driver);
    }

    /**
     * Open settings option by name
     * @param optionName settings option name
     */
    public void openSettingsOption(String optionName) {
        logger.info("Opening settings option: {}", optionName);
        if (!isTextDisplayed(optionName)) {
            // Try scrolling to find it
            gestureUtils.swipeUp(GestureUtils.SLOW_SWIPE);
            sleep(500);
        }
        clickByText(optionName);
        sleep(1500);
    }
}
