#include "autonav.h"
#include "stabilizer.h"
#include "commander.h"
#include "log.h"

#define AUTONAV_TIMEOUT_MS 30000

static uint32_t lastCommandTime = 0;
static uint8_t currentShape = 0;
static bool obstacleDetected = false;

void autonavInit(void) {
    lastCommandTime = 0;
    currentShape = 0;
    obstacleDetected = false;
}

void autonavKickSafety(void) {
    lastCommandTime = xTaskGetTickCount() * portTICK_PERIOD_MS;
}

void autonavSetObstacle(bool detected) {
    obstacleDetected = detected;
}

void autonavStartShape(uint8_t shapeId) {
    currentShape = shapeId;
    autonavKickSafety();
    LOG_I("AUTONAV", "Starting shape ID=%d", shapeId);
}

void autonavUpdate(uint32_t tickMs) {
    // Check safety timeout
    if (lastCommandTime > 0 && (tickMs - lastCommandTime) > AUTONAV_TIMEOUT_MS) {
        LOG_W("AUTONAV", "No command for 30s → Landing!");
        commanderLand();
        currentShape = 0;
        return;
    }

    if (obstacleDetected) {
        LOG_W("AUTONAV", "Obstacle detected → Holding position");
        commanderHover();  // Replace with proper hover
        return;
    }

    switch (currentShape) {
        case 1: // Square
            // TODO: implement square trajectory
            break;
        case 2: // Circle
            // TODO: implement circle trajectory
            break;
        default:
            break;
    }
}
