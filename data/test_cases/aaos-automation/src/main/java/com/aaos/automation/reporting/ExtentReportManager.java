package com.aaos.automation.reporting;

import com.aaos.automation.config.ConfigManager;
import com.aventstack.extentreports.ExtentReports;
import com.aventstack.extentreports.ExtentTest;
import com.aventstack.extentreports.reporter.ExtentSparkReporter;
import com.aventstack.extentreports.reporter.configuration.Theme;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.io.File;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

/**
 * Extent Report Manager for AAOS UI Automation
 * Generates HTML test reports with screenshots and logs
 */
public class ExtentReportManager {
    private static final Logger logger = LogManager.getLogger(ExtentReportManager.class);
    private static ExtentReports extentReports;
    private static final ThreadLocal<ExtentTest> extentTestThreadLocal = new ThreadLocal<>();
    private static String reportPath;

    private ExtentReportManager() {
        // Private constructor
    }

    /**
     * Initialize Extent Reports
     */
    public static synchronized void initializeReport() {
        if (extentReports == null) {
            ConfigManager config = ConfigManager.getInstance();
            
            // Create report directory
            String reportDir = config.getReportDir();
            new File(reportDir).mkdirs();
            
            // Generate report filename with timestamp
            String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
            reportPath = reportDir + File.separator + config.getReportName() + "_" + timestamp + ".html";
            
            // Configure Extent Spark Reporter
            ExtentSparkReporter sparkReporter = new ExtentSparkReporter(reportPath);
            sparkReporter.config().setTheme(Theme.STANDARD);
            sparkReporter.config().setDocumentTitle("AAOS UI Automation Report");
            sparkReporter.config().setReportName("Android Automotive OS - Car Display UI Tests");
            sparkReporter.config().setTimeStampFormat("yyyy-MM-dd HH:mm:ss");
            sparkReporter.config().setEncoding("UTF-8");
            
            // Create ExtentReports and attach reporter
            extentReports = new ExtentReports();
            extentReports.attachReporter(sparkReporter);
            
            // Set system info
            extentReports.setSystemInfo("Platform", "Android Automotive OS");
            extentReports.setSystemInfo("Device", config.getDeviceName());
            extentReports.setSystemInfo("Android Version", config.getPlatformVersion());
            extentReports.setSystemInfo("Automation Framework", "Appium + TestNG");
            extentReports.setSystemInfo("Display Resolution", 
                config.getDisplayWidth() + "x" + config.getDisplayHeight());
            
            logger.info("Extent Reports initialized. Report path: {}", reportPath);
        }
    }

    /**
     * Create a new test entry
     * @param testName test name
     * @param description test description
     * @return ExtentTest instance
     */
    public static ExtentTest createTest(String testName, String description) {
        ExtentTest test = extentReports.createTest(testName, description);
        extentTestThreadLocal.set(test);
        return test;
    }

    /**
     * Create a test with category
     * @param testName test name
     * @param description test description
     * @param category test category
     * @return ExtentTest instance
     */
    public static ExtentTest createTest(String testName, String description, String category) {
        ExtentTest test = createTest(testName, description);
        test.assignCategory(category);
        return test;
    }

    /**
     * Get current ExtentTest instance
     * @return ExtentTest instance
     */
    public static ExtentTest getTest() {
        return extentTestThreadLocal.get();
    }

    /**
     * Flush and write report to file
     */
    public static void flushReport() {
        if (extentReports != null) {
            extentReports.flush();
            logger.info("Extent Report generated: {}", reportPath);
        }
    }

    /**
     * Get the report file path
     * @return report file path
     */
    public static String getReportPath() {
        return reportPath;
    }
}
