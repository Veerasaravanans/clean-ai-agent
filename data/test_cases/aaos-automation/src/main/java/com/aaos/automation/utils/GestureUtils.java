package com.aaos.automation.utils;

import com.aaos.automation.config.ConfigManager;
import io.appium.java_client.android.AndroidDriver;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.openqa.selenium.Dimension;
import org.openqa.selenium.Point;
import org.openqa.selenium.interactions.Pause;
import org.openqa.selenium.interactions.PointerInput;
import org.openqa.selenium.interactions.Sequence;

import java.time.Duration;
import java.util.Arrays;
import java.util.Collections;

/**
 * Gesture Utilities for AAOS Car Display Automation
 * Provides touch gestures like tap, swipe, long press, drag and drop
 */
public class GestureUtils {
    private static final Logger logger = LogManager.getLogger(GestureUtils.class);
    private final AndroidDriver driver;
    private final int screenWidth;
    private final int screenHeight;

    // Swipe speed constants
    public static final int FAST_SWIPE = 200;
    public static final int MEDIUM_SWIPE = 500;
    public static final int SLOW_SWIPE = 1000;

    public GestureUtils(AndroidDriver driver) {
        this.driver = driver;
        ConfigManager config = ConfigManager.getInstance();
        this.screenWidth = config.getDisplayWidth();
        this.screenHeight = config.getDisplayHeight();
    }

    /**
     * Single tap at coordinates
     * @param x x coordinate
     * @param y y coordinate
     */
    public void tap(int x, int y) {
        logger.info("Tapping at coordinates: ({}, {})", x, y);
        
        PointerInput finger = new PointerInput(PointerInput.Kind.TOUCH, "finger");
        Sequence tap = new Sequence(finger, 1);
        
        tap.addAction(finger.createPointerMove(Duration.ZERO, PointerInput.Origin.viewport(), x, y));
        tap.addAction(finger.createPointerDown(PointerInput.MouseButton.LEFT.asArg()));
        tap.addAction(new Pause(finger, Duration.ofMillis(100)));
        tap.addAction(finger.createPointerUp(PointerInput.MouseButton.LEFT.asArg()));
        
        driver.perform(Collections.singletonList(tap));
    }

    /**
     * Double tap at coordinates
     * @param x x coordinate
     * @param y y coordinate
     */
    public void doubleTap(int x, int y) {
        logger.info("Double tapping at coordinates: ({}, {})", x, y);
        
        PointerInput finger = new PointerInput(PointerInput.Kind.TOUCH, "finger");
        Sequence doubleTap = new Sequence(finger, 1);
        
        // First tap
        doubleTap.addAction(finger.createPointerMove(Duration.ZERO, PointerInput.Origin.viewport(), x, y));
        doubleTap.addAction(finger.createPointerDown(PointerInput.MouseButton.LEFT.asArg()));
        doubleTap.addAction(new Pause(finger, Duration.ofMillis(50)));
        doubleTap.addAction(finger.createPointerUp(PointerInput.MouseButton.LEFT.asArg()));
        
        // Brief pause between taps
        doubleTap.addAction(new Pause(finger, Duration.ofMillis(100)));
        
        // Second tap
        doubleTap.addAction(finger.createPointerDown(PointerInput.MouseButton.LEFT.asArg()));
        doubleTap.addAction(new Pause(finger, Duration.ofMillis(50)));
        doubleTap.addAction(finger.createPointerUp(PointerInput.MouseButton.LEFT.asArg()));
        
        driver.perform(Collections.singletonList(doubleTap));
    }

    /**
     * Long press at coordinates
     * @param x x coordinate
     * @param y y coordinate
     * @param durationMillis duration in milliseconds
     */
    public void longPress(int x, int y, long durationMillis) {
        logger.info("Long pressing at coordinates: ({}, {}) for {}ms", x, y, durationMillis);
        
        PointerInput finger = new PointerInput(PointerInput.Kind.TOUCH, "finger");
        Sequence longPress = new Sequence(finger, 1);
        
        longPress.addAction(finger.createPointerMove(Duration.ZERO, PointerInput.Origin.viewport(), x, y));
        longPress.addAction(finger.createPointerDown(PointerInput.MouseButton.LEFT.asArg()));
        longPress.addAction(new Pause(finger, Duration.ofMillis(durationMillis)));
        longPress.addAction(finger.createPointerUp(PointerInput.MouseButton.LEFT.asArg()));
        
        driver.perform(Collections.singletonList(longPress));
    }

    /**
     * Swipe from start to end coordinates
     * @param startX start x coordinate
     * @param startY start y coordinate
     * @param endX end x coordinate
     * @param endY end y coordinate
     * @param durationMillis swipe duration in milliseconds
     */
    public void swipe(int startX, int startY, int endX, int endY, int durationMillis) {
        logger.info("Swiping from ({}, {}) to ({}, {}) in {}ms", startX, startY, endX, endY, durationMillis);
        
        PointerInput finger = new PointerInput(PointerInput.Kind.TOUCH, "finger");
        Sequence swipe = new Sequence(finger, 1);
        
        swipe.addAction(finger.createPointerMove(Duration.ZERO, PointerInput.Origin.viewport(), startX, startY));
        swipe.addAction(finger.createPointerDown(PointerInput.MouseButton.LEFT.asArg()));
        swipe.addAction(finger.createPointerMove(Duration.ofMillis(durationMillis), 
            PointerInput.Origin.viewport(), endX, endY));
        swipe.addAction(finger.createPointerUp(PointerInput.MouseButton.LEFT.asArg()));
        
        driver.perform(Collections.singletonList(swipe));
    }

    /**
     * Swipe left on screen
     * @param speed swipe speed (FAST_SWIPE, MEDIUM_SWIPE, SLOW_SWIPE)
     */
    public void swipeLeft(int speed) {
        int startX = (int) (screenWidth * 0.8);
        int endX = (int) (screenWidth * 0.2);
        int y = screenHeight / 2;
        swipe(startX, y, endX, y, speed);
    }

    /**
     * Swipe right on screen
     * @param speed swipe speed
     */
    public void swipeRight(int speed) {
        int startX = (int) (screenWidth * 0.2);
        int endX = (int) (screenWidth * 0.8);
        int y = screenHeight / 2;
        swipe(startX, y, endX, y, speed);
    }

    /**
     * Swipe up on screen
     * @param speed swipe speed
     */
    public void swipeUp(int speed) {
        int x = screenWidth / 2;
        int startY = (int) (screenHeight * 0.8);
        int endY = (int) (screenHeight * 0.2);
        swipe(x, startY, x, endY, speed);
    }

    /**
     * Swipe down on screen
     * @param speed swipe speed
     */
    public void swipeDown(int speed) {
        int x = screenWidth / 2;
        int startY = (int) (screenHeight * 0.2);
        int endY = (int) (screenHeight * 0.8);
        swipe(x, startY, x, endY, speed);
    }

    /**
     * Swipe up on the left side of the screen
     * @param speed swipe speed
     */
    public void swipeUpLeft(int speed) {
        int x = (int) (screenWidth * 0.2);
        int startY = (int) (screenHeight * 0.8);
        int endY = (int) (screenHeight * 0.2);
        swipe(x, startY, x, endY, speed);
    }

    /**
     * Swipe towards left (for opening app drawer)
     * @param speed swipe speed
     */
    public void swipeTowardsLeft(int speed) {
        // Start from right edge and swipe left to open drawer
        int startX = screenWidth - 50;
        int endX = 50;
        int y = screenHeight / 2;
        swipe(startX, y, endX, y, speed);
    }

    /**
     * Drag and drop operation
     * @param startX start x coordinate
     * @param startY start y coordinate
     * @param endX end x coordinate
     * @param endY end y coordinate
     */
    public void dragAndDrop(int startX, int startY, int endX, int endY) {
        logger.info("Dragging from ({}, {}) to ({}, {})", startX, startY, endX, endY);
        
        PointerInput finger = new PointerInput(PointerInput.Kind.TOUCH, "finger");
        Sequence drag = new Sequence(finger, 1);
        
        // Long press to initiate drag
        drag.addAction(finger.createPointerMove(Duration.ZERO, PointerInput.Origin.viewport(), startX, startY));
        drag.addAction(finger.createPointerDown(PointerInput.MouseButton.LEFT.asArg()));
        drag.addAction(new Pause(finger, Duration.ofMillis(500))); // Hold to initiate drag
        
        // Move to destination
        drag.addAction(finger.createPointerMove(Duration.ofMillis(800), 
            PointerInput.Origin.viewport(), endX, endY));
        drag.addAction(new Pause(finger, Duration.ofMillis(200))); // Brief pause before release
        drag.addAction(finger.createPointerUp(PointerInput.MouseButton.LEFT.asArg()));
        
        driver.perform(Collections.singletonList(drag));
    }

    /**
     * Drag element by offset
     * @param startX start x coordinate
     * @param startY start y coordinate
     * @param offsetX horizontal offset in pixels
     * @param offsetY vertical offset in pixels
     */
    public void dragByOffset(int startX, int startY, int offsetX, int offsetY) {
        dragAndDrop(startX, startY, startX + offsetX, startY + offsetY);
    }

    /**
     * Pinch in gesture (zoom out)
     * @param centerX center x coordinate
     * @param centerY center y coordinate
     */
    public void pinchIn(int centerX, int centerY) {
        logger.info("Pinch in at center: ({}, {})", centerX, centerY);
        
        PointerInput finger1 = new PointerInput(PointerInput.Kind.TOUCH, "finger1");
        PointerInput finger2 = new PointerInput(PointerInput.Kind.TOUCH, "finger2");
        
        int offset = 200;
        
        Sequence seq1 = new Sequence(finger1, 1);
        seq1.addAction(finger1.createPointerMove(Duration.ZERO, PointerInput.Origin.viewport(), 
            centerX - offset, centerY));
        seq1.addAction(finger1.createPointerDown(PointerInput.MouseButton.LEFT.asArg()));
        seq1.addAction(finger1.createPointerMove(Duration.ofMillis(500), 
            PointerInput.Origin.viewport(), centerX - 50, centerY));
        seq1.addAction(finger1.createPointerUp(PointerInput.MouseButton.LEFT.asArg()));
        
        Sequence seq2 = new Sequence(finger2, 1);
        seq2.addAction(finger2.createPointerMove(Duration.ZERO, PointerInput.Origin.viewport(), 
            centerX + offset, centerY));
        seq2.addAction(finger2.createPointerDown(PointerInput.MouseButton.LEFT.asArg()));
        seq2.addAction(finger2.createPointerMove(Duration.ofMillis(500), 
            PointerInput.Origin.viewport(), centerX + 50, centerY));
        seq2.addAction(finger2.createPointerUp(PointerInput.MouseButton.LEFT.asArg()));
        
        driver.perform(Arrays.asList(seq1, seq2));
    }

    /**
     * Pinch out gesture (zoom in)
     * @param centerX center x coordinate
     * @param centerY center y coordinate
     */
    public void pinchOut(int centerX, int centerY) {
        logger.info("Pinch out at center: ({}, {})", centerX, centerY);
        
        PointerInput finger1 = new PointerInput(PointerInput.Kind.TOUCH, "finger1");
        PointerInput finger2 = new PointerInput(PointerInput.Kind.TOUCH, "finger2");
        
        int offset = 50;
        int endOffset = 200;
        
        Sequence seq1 = new Sequence(finger1, 1);
        seq1.addAction(finger1.createPointerMove(Duration.ZERO, PointerInput.Origin.viewport(), 
            centerX - offset, centerY));
        seq1.addAction(finger1.createPointerDown(PointerInput.MouseButton.LEFT.asArg()));
        seq1.addAction(finger1.createPointerMove(Duration.ofMillis(500), 
            PointerInput.Origin.viewport(), centerX - endOffset, centerY));
        seq1.addAction(finger1.createPointerUp(PointerInput.MouseButton.LEFT.asArg()));
        
        Sequence seq2 = new Sequence(finger2, 1);
        seq2.addAction(finger2.createPointerMove(Duration.ZERO, PointerInput.Origin.viewport(), 
            centerX + offset, centerY));
        seq2.addAction(finger2.createPointerDown(PointerInput.MouseButton.LEFT.asArg()));
        seq2.addAction(finger2.createPointerMove(Duration.ofMillis(500), 
            PointerInput.Origin.viewport(), centerX + endOffset, centerY));
        seq2.addAction(finger2.createPointerUp(PointerInput.MouseButton.LEFT.asArg()));
        
        driver.perform(Arrays.asList(seq1, seq2));
    }

    /**
     * Parse swipe command from test case step
     * Format: "swipe:startX,startY,endX,endY (speed)"
     * @param swipeCommand the swipe command string
     */
    public void executeSwipeCommand(String swipeCommand) {
        // Parse command like "swipe:100,396,1308,396 (medium)"
        String coords = swipeCommand.replaceAll("swipe:", "").trim();
        String speedStr = "medium";
        
        if (coords.contains("(")) {
            int speedStart = coords.indexOf("(");
            speedStr = coords.substring(speedStart + 1, coords.indexOf(")")).trim();
            coords = coords.substring(0, speedStart).trim();
        }
        
        String[] parts = coords.split(",");
        int startX = Integer.parseInt(parts[0].trim());
        int startY = Integer.parseInt(parts[1].trim());
        int endX = Integer.parseInt(parts[2].trim());
        int endY = Integer.parseInt(parts[3].trim());
        
        int speed = switch (speedStr.toLowerCase()) {
            case "fast" -> FAST_SWIPE;
            case "slow" -> SLOW_SWIPE;
            default -> MEDIUM_SWIPE;
        };
        
        swipe(startX, startY, endX, endY, speed);
    }
}
