package com.aaos.automation.pages;

import io.appium.java_client.android.AndroidDriver;
import org.openqa.selenium.By;

/**
 * Bluetooth Settings Page Object for AAOS Car Display
 * Represents the Bluetooth settings page
 */
public class BluetoothSettingsPage extends BasePage {

    // Bluetooth settings locators
    private static final By BLUETOOTH_TOGGLE = By.id("com.android.car.settings:id/toggle_switch");
    private static final By PAIRED_DEVICES = By.xpath("//*[@text='Paired devices']");
    private static final By AVAILABLE_DEVICES = By.xpath("//*[@text='Available devices']");
    private static final By BLUETOOTH_TITLE = By.xpath("//*[@text='Bluetooth']");

    public BluetoothSettingsPage(AndroidDriver driver) {
        super(driver);
    }

    @Override
    public boolean isPageLoaded() {
        return isTextDisplayed("Bluetooth") || isElementDisplayed(BLUETOOTH_TOGGLE);
    }

    @Override  
    public String getPageIdentifier() {
        return "Bluetooth Settings";
    }

    /**
     * Toggle Bluetooth on/off
     */
    public void toggleBluetooth() {
        logger.info("Toggling Bluetooth");
        if (isElementDisplayed(BLUETOOTH_TOGGLE)) {
            click(BLUETOOTH_TOGGLE);
            sleep(2000);
        }
    }

    /**
     * Check if Bluetooth is enabled
     * @return true if enabled
     */
    public boolean isBluetoothEnabled() {
        // Check for toggle state or presence of device lists
        return isElementDisplayed(PAIRED_DEVICES) || isElementDisplayed(AVAILABLE_DEVICES);
    }

    /**
     * Check if paired devices section is visible
     * @return true if visible
     */
    public boolean isPairedDevicesVisible() {
        return isElementDisplayed(PAIRED_DEVICES);
    }

    /**
     * Check if available devices section is visible
     * @return true if visible
     */
    public boolean isAvailableDevicesVisible() {
        return isElementDisplayed(AVAILABLE_DEVICES);
    }

    /**
     * Click on a paired device
     * @param deviceName device name
     */
    public void selectPairedDevice(String deviceName) {
        logger.info("Selecting paired device: {}", deviceName);
        clickByText(deviceName);
        sleep(1000);
    }

    /**
     * Click on an available device to pair
     * @param deviceName device name
     */
    public void pairDevice(String deviceName) {
        logger.info("Pairing with device: {}", deviceName);
        clickByText(deviceName);
        sleep(3000);
    }

    /**
     * Scan for available Bluetooth devices
     */
    public void scanForDevices() {
        logger.info("Scanning for Bluetooth devices");
        if (isTextDisplayed("Refresh")) {
            clickByText("Refresh");
        } else if (isTextDisplayed("Scan")) {
            clickByText("Scan");
        }
        sleep(5000);
    }
}
