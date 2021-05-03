// SPDX-License-Identifier: CC0-1.0

#include "bsp/board.h"
#include "tusb.h"

#include "usbtest.h"

static uint32_t led_on_ms, led_off_ms;

static void board_led_blink_on(uint32_t off_ms)
{
    board_led_on();
    led_on_ms = 0;
    led_off_ms = off_ms;
}

static void board_led_blink_off(uint32_t on_ms)
{
    board_led_off();
    led_on_ms = on_ms;
    led_off_ms = 0;
}

void board_led_activity(void)
{
    board_led_blink_on(board_millis() + 10); // blink on 10ms
}

static void board_led_task(void)
{
    uint32_t now_ms = board_millis();

    if (led_off_ms && now_ms >= led_off_ms)
        board_led_blink_off(now_ms + 5000); // schedule new idle blink in 5 seconds
    else if (led_on_ms && now_ms >= led_on_ms)
        board_led_blink_on(now_ms + 1000); // idle blink on for one second
}

int main(void)
{
    board_init();
    tusb_init();

    printf("usbtest\n");

    board_led_blink_on(board_millis() + 100);

    while (1)
    {
        tud_task();
        board_led_task();
    }

    return 0;
}
