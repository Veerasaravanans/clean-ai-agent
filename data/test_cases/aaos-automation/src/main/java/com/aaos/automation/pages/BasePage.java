package com.aaos.automation.pages;

import com.aaos.automation.utils.GestureUtils;
import com.aaos.automation.utils.WaitUtils;
import io.appium.java_client.android.AndroidDriver;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.openqa.selenium.By;
import org.openqa.selenium.WebElement;

/**
 * Base Page Object for AAOS UI Automation
 * Provides common functionality for all page objects
 */
public abstract class BasePage {
    protected static final Logger logger = LogManager.getLogger(BasePage.class);
    protected final AndroidDriver driver;
    protected final GestureUtils gestureUtils;
    protected final WaitUtils waitUtils;

    // Common locators for AAOS car display
    protected static final By HOME_BUTTON = By.id("com.android.car.carlauncher:id/nav_icon_home");
    protected static final By BACK_BUTTON = By.xpath("//android.widget.ImageButton[@content-desc='Back']");
    protected static final By APP_LAUNCHER_BUTTON = By.id("com.android.car.carlauncher:id/apps_button");

    public BasePage(AndroidDriver driver) {
        this.driver = driver;
        this.gestureUtils = new GestureUtils(driver);
        this.waitUtils = new WaitUtils(driver);
    }

    /**
     * Check if current page is loaded
     * @return true if page is loaded
     */
    public abstract boolean isPageLoaded();

    /**
     * Get page title or identifier
     * @return page identifier
     */
    public abstract String getPageIdentifier();

    /**
     * Click on element by locator
     * @param locator element locator
     */
    protected void click(By locator) {
        logger.debug("Clicking element: {}", locator);
        waitUtils.waitForClickable(locator).click();
    }

    /**
     * Click on element by text
     * @param text text to find and click
     */
    protected void clickByText(String text) {
        logger.debug("Clicking element with text: {}", text);
        By locator = By.xpath("//*[@text='" + text + "']");
        waitUtils.waitForClickable(locator).click();
    }

    /**
     * Click on element containing text
     * @param text partial text to find
     */
    protected void clickByContainingText(String text) {
        logger.debug("Clicking element containing text: {}", text);
        By locator = By.xpath("//*[contains(@text, '" + text + "')]");
        waitUtils.waitForClickable(locator).click();
    }

    /**
     * Get element text
     * @param locator element locator
     * @return element text
     */
    protected String getText(By locator) {
        return waitUtils.waitForVisibility(locator).getText();
    }

    /**
     * Check if element is displayed
     * @param locator element locator
     * @return true if element is displayed
     */
    protected boolean isElementDisplayed(By locator) {
        return waitUtils.isElementDisplayed(locator);
    }

    /**
     * Check if element with text is displayed
     * @param text text to find
     * @return true if element is displayed
     */
    protected boolean isTextDisplayed(String text) {
        By locator = By.xpath("//*[@text='" + text + "']");
        return waitUtils.isElementDisplayed(locator);
    }

    /**
     * Navigate to home screen
     */
    public void goHome() {
        logger.info("Navigating to home screen");
        if (isElementDisplayed(HOME_BUTTON)) {
            click(HOME_BUTTON);
        } else {
            gestureUtils.tap(100, 740); // Default home button position
        }
        waitUtils.waitForScreenLoad();
    }

    /**
     * Press back button
     */
    public void goBack() {
        logger.info("Pressing back button");
        if (isElementDisplayed(BACK_BUTTON)) {
            click(BACK_BUTTON);
        } else {
            driver.navigate().back();
        }
        waitUtils.waitForScreenLoad();
    }

    /**
     * Wait for specified milliseconds
     * @param millis time to wait
     */
    protected void sleep(long millis) {
        waitUtils.waitMillis(millis);
    }

    /**
     * Find element by resource id
     * @param resourceId element resource id
     * @return WebElement
     */
    protected WebElement findById(String resourceId) {
        return driver.findElement(By.id(resourceId));
    }

    /**
     * Find element by accessibility id
     * @param accessibilityId element accessibility id
     * @return WebElement
     */
    protected WebElement findByAccessibilityId(String accessibilityId) {
        return driver.findElement(By.xpath("//*[@content-desc='" + accessibilityId + "']"));
    }

    /**
     * Scroll down to find element
     * @param text text to find
     */
    protected void scrollToText(String text) {
        logger.debug("Scrolling to find text: {}", text);
        String uiAutomatorCommand = "new UiScrollable(new UiSelector().scrollable(true))" +
            ".scrollIntoView(new UiSelector().text(\"" + text + "\"))";
        driver.findElement(By.xpath("//*[@text='" + text + "']"));
    }
}
