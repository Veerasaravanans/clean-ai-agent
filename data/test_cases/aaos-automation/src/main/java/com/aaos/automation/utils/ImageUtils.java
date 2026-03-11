package com.aaos.automation.utils;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import javax.imageio.ImageIO;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;

/**
 * Image Utilities for SSIM comparison and image manipulation
 * Used for verifying UI elements in AAOS car display
 */
public class ImageUtils {
    private static final Logger logger = LogManager.getLogger(ImageUtils.class);

    /**
     * Calculate SSIM (Structural Similarity Index) between two images
     * @param imagePath1 path to first image
     * @param imagePath2 path to second image
     * @return SSIM value between 0 and 1
     */
    public static double calculateSSIM(String imagePath1, String imagePath2) {
        try {
            BufferedImage img1 = ImageIO.read(new File(imagePath1));
            BufferedImage img2 = ImageIO.read(new File(imagePath2));
            
            return calculateSSIM(img1, img2);
        } catch (IOException e) {
            logger.error("Failed to read images for SSIM calculation: {}", e.getMessage());
            return 0.0;
        }
    }

    /**
     * Calculate SSIM between two BufferedImages
     * @param img1 first image
     * @param img2 second image
     * @return SSIM value
     */
    public static double calculateSSIM(BufferedImage img1, BufferedImage img2) {
        // Resize images to same size if needed
        int width = Math.min(img1.getWidth(), img2.getWidth());
        int height = Math.min(img1.getHeight(), img2.getHeight());
        
        if (img1.getWidth() != width || img1.getHeight() != height) {
            img1 = resizeImage(img1, width, height);
        }
        if (img2.getWidth() != width || img2.getHeight() != height) {
            img2 = resizeImage(img2, width, height);
        }

        // SSIM constants
        double C1 = 6.5025;  // (0.01 * 255)^2
        double C2 = 58.5225; // (0.03 * 255)^2

        double[] mean1 = calculateMean(img1);
        double[] mean2 = calculateMean(img2);
        double[] variance1 = calculateVariance(img1, mean1);
        double[] variance2 = calculateVariance(img2, mean2);
        double[] covariance = calculateCovariance(img1, img2, mean1, mean2);

        double ssimSum = 0;
        for (int i = 0; i < 3; i++) { // RGB channels
            double numerator = (2 * mean1[i] * mean2[i] + C1) * (2 * covariance[i] + C2);
            double denominator = (mean1[i] * mean1[i] + mean2[i] * mean2[i] + C1) * 
                                (variance1[i] + variance2[i] + C2);
            ssimSum += numerator / denominator;
        }

        return ssimSum / 3.0; // Average across RGB channels
    }

    /**
     * Crop image to specified region
     * @param sourcePath source image path
     * @param destPath destination image path
     * @param x region x coordinate
     * @param y region y coordinate
     * @param width region width
     * @param height region height
     */
    public static void cropImage(String sourcePath, String destPath, int x, int y, int width, int height) 
            throws IOException {
        BufferedImage source = ImageIO.read(new File(sourcePath));
        
        // Validate bounds
        x = Math.max(0, x);
        y = Math.max(0, y);
        width = Math.min(width, source.getWidth() - x);
        height = Math.min(height, source.getHeight() - y);
        
        BufferedImage cropped = source.getSubimage(x, y, width, height);
        ImageIO.write(cropped, "png", new File(destPath));
        logger.info("Image cropped and saved to: {}", destPath);
    }

    /**
     * Resize image to specified dimensions
     * @param original original image
     * @param width target width
     * @param height target height
     * @return resized image
     */
    public static BufferedImage resizeImage(BufferedImage original, int width, int height) {
        BufferedImage resized = new BufferedImage(width, height, original.getType());
        Graphics2D g = resized.createGraphics();
        g.setRenderingHint(RenderingHints.KEY_INTERPOLATION, RenderingHints.VALUE_INTERPOLATION_BILINEAR);
        g.drawImage(original, 0, 0, width, height, null);
        g.dispose();
        return resized;
    }

    /**
     * Calculate mean pixel values for RGB channels
     */
    private static double[] calculateMean(BufferedImage img) {
        double[] mean = new double[3];
        int pixelCount = img.getWidth() * img.getHeight();

        for (int y = 0; y < img.getHeight(); y++) {
            for (int x = 0; x < img.getWidth(); x++) {
                int rgb = img.getRGB(x, y);
                mean[0] += (rgb >> 16) & 0xFF; // Red
                mean[1] += (rgb >> 8) & 0xFF;  // Green
                mean[2] += rgb & 0xFF;          // Blue
            }
        }

        for (int i = 0; i < 3; i++) {
            mean[i] /= pixelCount;
        }

        return mean;
    }

    /**
     * Calculate variance for RGB channels
     */
    private static double[] calculateVariance(BufferedImage img, double[] mean) {
        double[] variance = new double[3];
        int pixelCount = img.getWidth() * img.getHeight();

        for (int y = 0; y < img.getHeight(); y++) {
            for (int x = 0; x < img.getWidth(); x++) {
                int rgb = img.getRGB(x, y);
                double r = ((rgb >> 16) & 0xFF) - mean[0];
                double g = ((rgb >> 8) & 0xFF) - mean[1];
                double b = (rgb & 0xFF) - mean[2];
                
                variance[0] += r * r;
                variance[1] += g * g;
                variance[2] += b * b;
            }
        }

        for (int i = 0; i < 3; i++) {
            variance[i] /= pixelCount;
        }

        return variance;
    }

    /**
     * Calculate covariance between two images for RGB channels
     */
    private static double[] calculateCovariance(BufferedImage img1, BufferedImage img2, 
                                                 double[] mean1, double[] mean2) {
        double[] covariance = new double[3];
        int pixelCount = img1.getWidth() * img1.getHeight();

        for (int y = 0; y < img1.getHeight(); y++) {
            for (int x = 0; x < img1.getWidth(); x++) {
                int rgb1 = img1.getRGB(x, y);
                int rgb2 = img2.getRGB(x, y);
                
                covariance[0] += (((rgb1 >> 16) & 0xFF) - mean1[0]) * (((rgb2 >> 16) & 0xFF) - mean2[0]);
                covariance[1] += (((rgb1 >> 8) & 0xFF) - mean1[1]) * (((rgb2 >> 8) & 0xFF) - mean2[1]);
                covariance[2] += ((rgb1 & 0xFF) - mean1[2]) * ((rgb2 & 0xFF) - mean2[2]);
            }
        }

        for (int i = 0; i < 3; i++) {
            covariance[i] /= pixelCount;
        }

        return covariance;
    }

    /**
     * Compare two images and return match percentage
     * @param imagePath1 first image path
     * @param imagePath2 second image path
     * @return match percentage (0-100)
     */
    public static double compareImages(String imagePath1, String imagePath2) {
        double ssim = calculateSSIM(imagePath1, imagePath2);
        return ssim * 100;
    }

    /**
     * Parse verification region string
     * Format: "x,y,width,height"
     * @param regionString region string from test case
     * @return int array [x, y, width, height]
     */
    public static int[] parseRegion(String regionString) {
        String[] parts = regionString.split(",");
        return new int[] {
            Integer.parseInt(parts[0].trim()),
            Integer.parseInt(parts[1].trim()),
            Integer.parseInt(parts[2].trim()),
            Integer.parseInt(parts[3].trim())
        };
    }
}
