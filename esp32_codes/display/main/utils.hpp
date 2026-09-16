#ifndef UTILS_H
# define UTILS_H

#include <WiFi.h>
#include <string>


int     connect_to_wifi();
void    print_raw_bites(uint8_t *data, const uint32_t size);
void    display_gaps_between_frames(WiFiClient *stream);


#endif