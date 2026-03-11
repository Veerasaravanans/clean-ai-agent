package com.aaos.automation.pages;

import io.appium.java_client.android.AndroidDriver;
import org.openqa.selenium.By;
import org.openqa.selenium.WebElement;

import java.util.List;

/**
 * Home Page Object for AAOS Car Display
 * Represents the main home screen of the car display
 */
public class HomePage extends BasePage {

    // Home screen locators
    private static final By HOME_CONTAINER = By.id("com.android.car.carlauncher:id/container");
    private static final By APPS_GRID = By.id("com.android.car.carlauncher:id/apps_grid");
    private static final By DOCK_BAR = By.id("com.android.car.carlauncher:id/dock");
    private static final By STATUS_BAR = By.id("com.android.car.systemui:id/status_bar");
    private static final By NAVIGATION_BAR = By.id("com.android.car.systemui:id/nav_buttons");
    private static final By APP_ICON = By.className("android.widget.ImageView");
    
    // App launcher related
    private static final By APP_LAUNCHER_DRAWER = By.id("com.android.car.carlauncher:id/apps_grid");
    private static final By ALL_APPS_BUTTON = By.xpath("//*[@content-desc='All apps']");

    public HomePage(AndroidDriver driver) {
        super(driver);
    }

    @Override
    public boolean isPageLoaded() {
        return isElementDisplayed(HOME_CONTAINER) || isElementDisplayed(DOCK_BAR);
    }

    @Override
    public String getPageIdentifier() {
        return "Home Screen";
    }

    /**
     * Open app launcher drawer by swiping left
     */
    public AppLauncherPage openAppLauncher() {
        logger.info("Opening app launcher drawer");
        
        // Swipe left to open app drawer
        gestureUtils.swipeTowardsLeft(GestureUtils.MEDIUM_SWIPE);
        sleep(1000);
        
        return new AppLauncherPage(driver);
    }

    /**
     * Open app launcher by tapping on apps button
     */
    public AppLauncherPage openAppLauncherByButton() {
        logger.info("Opening app launcher via button");
        
        if (isElementDisplayed(ALL_APPS_BUTTON)) {
            click(ALL_APPS_BUTTON);
        } else if (isElementDisplayed(APP_LAUNCHER_BUTTON)) {
            click(APP_LAUNCHER_BUTTON);
        } else {
            // Fallback: swipe to open
            return openAppLauncher();
        }
        sleep(1000);
        
        return new AppLauncherPage(driver);
    }

    /**
     * Check if app launcher drawer is visible
     * @return true if drawer is open
     */
    public boolean isAppLauncherOpen() {
        return isElementDisplayed(APP_LAUNCHER_DRAWER);
    }

    /**
     * Get list of dock app icons
     * @return list of dock app icons
     */
    public List<WebElement> getDockApps() {
        return driver.findElements(By.xpath("//android.widget.LinearLayout[@resource-id='com.android.car.carlauncher:id/dock']//android.widget.ImageView"));
    }

    /**
     * Check if an app is visible on home screen
     * @param appName name of the app
     * @return true if app is visible
     */
    public boolean isAppVisible(String appName) {
        return isTextDisplayed(appName);
    }

    /**
     * Open quick settings panel
     */
    public void openQuickSettings() {
        logger.info("Opening quick settings");
        gestureUtils.swipeDown(GestureUtils.MEDIUM_SWIPE);
        sleep(500);
    }

    /**
     * Return to home from any screen
     */
    public void returnToHome() {
        goHome();
    }
}
