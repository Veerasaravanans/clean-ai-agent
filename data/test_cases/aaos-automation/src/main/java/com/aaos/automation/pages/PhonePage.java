package com.aaos.automation.pages;

import io.appium.java_client.android.AndroidDriver;
import org.openqa.selenium.By;

/**
 * Phone Page Object for AAOS Car Display
 * Represents the Phone dialer application
 */
public class PhonePage extends BasePage {

    // Phone app locators
    private static final By DIALER_CONTAINER = By.id("com.android.car.dialer:id/fragment_container");
    private static final By DIALPAD = By.xpath("//*[@content-desc='Dialpad']");
    private static final By CALL_BUTTON = By.id("com.android.car.dialer:id/call_button");
    private static final By CONTACTS_TAB = By.xpath("//*[@text='Contacts']");
    private static final By RECENTS_TAB = By.xpath("//*[@text='Recents']");
    private static final By FAVORITES_TAB = By.xpath("//*[@text='Favorites']");
    private static final By DIAL_TAB = By.xpath("//*[@text='Dial']");

    // Dialpad buttons
    private static final String DIALPAD_BUTTON_TEMPLATE = "//*[@text='%s']";

    public PhonePage(AndroidDriver driver) {
        super(driver);
    }

    @Override
    public boolean isPageLoaded() {
        return isTextDisplayed("Dial") || 
               isTextDisplayed("Contacts") || 
               isTextDisplayed("Recents") ||
               isElementDisplayed(DIALER_CONTAINER);
    }

    @Override
    public String getPageIdentifier() {
        return "Phone";
    }

    /**
     * Check if dialer interface is displayed
     * @return true if dialer is visible
     */
    public boolean isDialerVisible() {
        return isTextDisplayed("Dial") || isElementDisplayed(CALL_BUTTON);
    }

    /**
     * Navigate to Contacts tab
     */
    public void goToContacts() {
        logger.info("Navigating to Contacts");
        clickByText("Contacts");
        sleep(1000);
    }

    /**
     * Navigate to Recents tab
     */
    public void goToRecents() {
        logger.info("Navigating to Recents");
        clickByText("Recents");
        sleep(1000);
    }

    /**
     * Navigate to Favorites tab
     */
    public void goToFavorites() {
        logger.info("Navigating to Favorites");
        clickByText("Favorites");
        sleep(1000);
    }

    /**
     * Navigate to Dial tab
     */
    public void goToDial() {
        logger.info("Navigating to Dial");
        clickByText("Dial");
        sleep(1000);
    }

    /**
     * Dial a phone number
     * @param phoneNumber phone number to dial
     */
    public void dialNumber(String phoneNumber) {
        logger.info("Dialing number: {}", phoneNumber);
        
        // Make sure we're on dial tab
        goToDial();
        
        // Enter each digit
        for (char digit : phoneNumber.toCharArray()) {
            clickByText(String.valueOf(digit));
            sleep(200);
        }
    }

    /**
     * Press call button
     */
    public void pressCall() {
        logger.info("Pressing call button");
        if (isElementDisplayed(CALL_BUTTON)) {
            click(CALL_BUTTON);
        } else {
            // Try finding by text
            clickByText("Call");
        }
        sleep(1000);
    }

    /**
     * Search for a contact
     * @param contactName contact name
     */
    public void searchContact(String contactName) {
        logger.info("Searching for contact: {}", contactName);
        goToContacts();
        if (isTextDisplayed("Search")) {
            clickByText("Search");
            sleep(500);
        }
        // Type search query if search field is available
    }

    /**
     * Call a contact by name
     * @param contactName contact name
     */
    public void callContact(String contactName) {
        logger.info("Calling contact: {}", contactName);
        goToContacts();
        clickByText(contactName);
        sleep(500);
        pressCall();
    }
}
