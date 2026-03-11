package com.aaos.automation.pages;

import io.appium.java_client.android.AndroidDriver;
import org.openqa.selenium.By;

/**
 * Spotify Page Object for AAOS Car Display
 * Represents the Spotify music application
 */
public class SpotifyPage extends BasePage {

    // Spotify locators
    private static final By SPOTIFY_CONTAINER = By.xpath("//*[contains(@resource-id, 'spotify')]");
    private static final By PLAY_BUTTON = By.xpath("//*[@content-desc='Play']");
    private static final By PAUSE_BUTTON = By.xpath("//*[@content-desc='Pause']");
    private static final By NEXT_BUTTON = By.xpath("//*[@content-desc='Next']");
    private static final By PREVIOUS_BUTTON = By.xpath("//*[@content-desc='Previous']");
    private static final By NOW_PLAYING = By.xpath("//*[contains(@text, 'Now Playing')]");

    public SpotifyPage(AndroidDriver driver) {
        super(driver);
    }

    @Override
    public boolean isPageLoaded() {
        // Check for Spotify specific elements or Spotify text
        return isTextDisplayed("Spotify") || 
               isTextDisplayed("Home") || 
               isTextDisplayed("Search") ||
               isTextDisplayed("Your Library");
    }

    @Override
    public String getPageIdentifier() {
        return "Spotify";
    }

    /**
     * Play current track
     */
    public void play() {
        logger.info("Playing track on Spotify");
        if (isElementDisplayed(PLAY_BUTTON)) {
            click(PLAY_BUTTON);
            sleep(1000);
        }
    }

    /**
     * Pause current track
     */
    public void pause() {
        logger.info("Pausing track on Spotify");
        if (isElementDisplayed(PAUSE_BUTTON)) {
            click(PAUSE_BUTTON);
            sleep(500);
        }
    }

    /**
     * Skip to next track
     */
    public void next() {
        logger.info("Skipping to next track");
        if (isElementDisplayed(NEXT_BUTTON)) {
            click(NEXT_BUTTON);
            sleep(1000);
        }
    }

    /**
     * Go to previous track
     */
    public void previous() {
        logger.info("Going to previous track");
        if (isElementDisplayed(PREVIOUS_BUTTON)) {
            click(PREVIOUS_BUTTON);
            sleep(1000);
        }
    }

    /**
     * Navigate to Home tab
     */
    public void goToHome() {
        clickByText("Home");
        sleep(1000);
    }

    /**
     * Navigate to Search
     */
    public void goToSearch() {
        clickByText("Search");
        sleep(1000);
    }

    /**
     * Navigate to Your Library
     */
    public void goToLibrary() {
        clickByText("Your Library");
        sleep(1000);
    }

    /**
     * Check if now playing view is displayed
     * @return true if playing view visible
     */
    public boolean isNowPlayingVisible() {
        return isElementDisplayed(NOW_PLAYING);
    }
}
