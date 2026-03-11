package com.aaos.automation.utils;

import com.aaos.automation.config.ConfigManager;
import io.appium.java_client.android.AndroidDriver;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.openqa.selenium.By;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;

import java.time.Duration;
import java.util.List;

/**
 * Wait Utilities for AAOS UI Automation
 * Provides explicit wait methods for element synchronization
 */
public class WaitUtils {
    private static final Logger logger = LogManager.getLogger(WaitUtils.class);
    private final WebDriverWait wait;
    private final AndroidDriver driver;

    public WaitUtils(AndroidDriver driver) {
        this.driver = driver;
        int timeout = ConfigManager.getInstance().getExplicitWait();
        this.wait = new WebDriverWait(driver, Duration.ofSeconds(timeout));
    }

    public WaitUtils(AndroidDriver driver, int timeoutSeconds) {
        this.driver = driver;
        this.wait = new WebDriverWait(driver, Duration.ofSeconds(timeoutSeconds));
    }

    /**
     * Wait for element to be visible
     * @param locator element locator
     * @return visible WebElement
     */
    public WebElement waitForVisibility(By locator) {
        logger.debug("Waiting for element visibility: {}", locator);
        return wait.until(ExpectedConditions.visibilityOfElementLocated(locator));
    }

    /**
     * Wait for element to be clickable
     * @param locator element locator
     * @return clickable WebElement
     */
    public WebElement waitForClickable(By locator) {
        logger.debug("Waiting for element to be clickable: {}", locator);
        return wait.until(ExpectedConditions.elementToBeClickable(locator));
    }

    /**
     * Wait for element to be present in DOM
     * @param locator element locator
     * @return WebElement
     */
    public WebElement waitForPresence(By locator) {
        logger.debug("Waiting for element presence: {}", locator);
        return wait.until(ExpectedConditions.presenceOfElementLocated(locator));
    }

    /**
     * Wait for element to disappear
     * @param locator element locator
     * @return true if element disappeared
     */
    public boolean waitForInvisibility(By locator) {
        logger.debug("Waiting for element invisibility: {}", locator);
        return wait.until(ExpectedConditions.invisibilityOfElementLocated(locator));
    }

    /**
     * Wait for text to be present in element
     * @param locator element locator
     * @param text expected text
     * @return true if text is present
     */
    public boolean waitForTextPresent(By locator, String text) {
        logger.debug("Waiting for text '{}' in element: {}", text, locator);
        return wait.until(ExpectedConditions.textToBePresentInElementLocated(locator, text));
    }

    /**
     * Wait for multiple elements to be visible
     * @param locator element locator
     * @return list of visible WebElements
     */
    public List<WebElement> waitForAllVisible(By locator) {
        logger.debug("Waiting for all elements visible: {}", locator);
        return wait.until(ExpectedConditions.visibilityOfAllElementsLocatedBy(locator));
    }

    /**
     * Wait with custom timeout
     * @param locator element locator
     * @param timeoutSeconds custom timeout
     * @return visible WebElement
     */
    public WebElement waitForVisibility(By locator, int timeoutSeconds) {
        WebDriverWait customWait = new WebDriverWait(driver, Duration.ofSeconds(timeoutSeconds));
        return customWait.until(ExpectedConditions.visibilityOfElementLocated(locator));
    }

    /**
     * Wait for element by text
     * @param text text to find
     * @return WebElement with matching text
     */
    public WebElement waitForElementByText(String text) {
        By locator = By.xpath("//*[@text='" + text + "']");
        return waitForVisibility(locator);
    }

    /**
     * Wait for element containing text
     * @param text partial text to find
     * @return WebElement containing text
     */
    public WebElement waitForElementContainingText(String text) {
        By locator = By.xpath("//*[contains(@text, '" + text + "')]");
        return waitForVisibility(locator);
    }

    /**
     * Check if element is displayed without throwing exception
     * @param locator element locator
     * @return true if element is displayed
     */
    public boolean isElementDisplayed(By locator) {
        try {
            return driver.findElement(locator).isDisplayed();
        } catch (Exception e) {
            return false;
        }
    }

    /**
     * Wait for screen to load (brief delay)
     */
    public void waitForScreenLoad() {
        try {
            Thread.sleep(1000);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    /**
     * Wait for specified milliseconds
     * @param millis time to wait in milliseconds
     */
    public void waitMillis(long millis) {
        try {
            Thread.sleep(millis);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}
