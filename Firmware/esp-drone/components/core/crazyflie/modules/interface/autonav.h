#pragma once

#include <stdbool.h>
#include <stdint.h>

// Initialize the autonomous navigation module
void autonavInit(void);

// Called periodically from the stabilizer loop
void autonavUpdate(uint32_t tickMs);

// Start a shape flight
void autonavStartShape(uint8_t shapeId);  
// 0 = stop, 1 = square, 2 = circle

// Reset the safety timer (called when any command is received)
void autonavKickSafety(void);

// Obstacle sensor hook
void autonavSetObstacle(bool detected);

#endif
