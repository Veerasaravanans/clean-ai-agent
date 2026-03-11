package com.aaos.automation.pages;

import io.appium.java_client.android.AndroidDriver;
import org.openqa.selenium.By;

/**
 * SMS/Messages Page Object for AAOS Car Display
 * Represents the messaging application
 */
public class SmsPage extends BasePage {

    // SMS app locators
    private static final By MESSAGES_CONTAINER = By.id("com.android.car.messenger:id/fragment_container");
    private static final By COMPOSE_BUTTON = By.xpath("//*[@content-desc='Compose']");
    private static final By MESSAGE_LIST = By.id("com.android.car.messenger:id/message_list");
    private static final By NEW_MESSAGE_BUTTON = By.xpath("//*[@text='New message']");

    public SmsPage(AndroidDriver driver) {
        super(driver);
    }

    @Override
    public boolean isPageLoaded() {
        return isTextDisplayed("Messages") || 
               isTextDisplayed("Conversations") ||
               isElementDisplayed(MESSAGES_CONTAINER);
    }

    @Override
    public String getPageIdentifier() {
        return "SMS/Messages";
    }

    /**
     * Check if messages interface is displayed
     * @return true if messages view is visible
     */
    public boolean isMessagesViewVisible() {
        return isTextDisplayed("Messages") || 
               isTextDisplayed("Conversations") ||
               isElementDisplayed(MESSAGE_LIST);
    }

    /**
     * Open compose new message
     */
    public void composeNewMessage() {
        logger.info("Opening compose new message");
        if (isElementDisplayed(COMPOSE_BUTTON)) {
            click(COMPOSE_BUTTON);
        } else if (isElementDisplayed(NEW_MESSAGE_BUTTON)) {
            click(NEW_MESSAGE_BUTTON);
        }
        sleep(1000);
    }

    /**
     * Open conversation by contact name
     * @param contactName contact name
     */
    public void openConversation(String contactName) {
        logger.info("Opening conversation with: {}", contactName);
        clickByText(contactName);
        sleep(1000);
    }

    /**
     * Check if there are any conversations
     * @return true if conversations exist
     */
    public boolean hasConversations() {
        return isElementDisplayed(MESSAGE_LIST);
    }

    /**
     * Read latest message (via voice or display)
     */
    public void readLatestMessage() {
        logger.info("Reading latest message");
        if (isTextDisplayed("Read")) {
            clickByText("Read");
            sleep(2000);
        }
    }

    /**
     * Reply to message with voice
     */
    public void replyWithVoice() {
        logger.info("Initiating voice reply");
        if (isTextDisplayed("Reply")) {
            clickByText("Reply");
            sleep(1000);
        }
    }
}
