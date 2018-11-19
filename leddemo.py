#!/usr/bin/env vpython
import time
from cffi import FFI

WS2811_STRIP_RGB                                =0x00100800
WS2811_STRIP_RBG                                =0x00100008
WS2811_STRIP_GRB                                =0x00081000
WS2811_STRIP_GBR                                =0x00080010
WS2811_STRIP_BRG                                =0x00001008
WS2811_STRIP_BGR                                =0x00000810

ffi = FFI()
ffi.cdef("""
#define RPI_PWM_CHANNELS 2
struct ws2811_device;

typedef uint32_t ws2811_led_t;                   //< 0xWWRRGGBB
typedef struct
{
    int gpionum;                                 //< GPIO Pin with PWM alternate function, 0 if unused
    int invert;                                  //< Invert output signal
    int count;                                   //< Number of LEDs, 0 if channel is unused
    int strip_type;                              //< Strip color layout -- one of WS2811_STRIP_xxx constants
    ws2811_led_t *leds;                          //< LED buffers, allocated by driver based on count
    uint8_t brightness;                          //< Brightness value between 0 and 255
    uint8_t wshift;                              //< White shift value
    uint8_t rshift;                              //< Red shift value
    uint8_t gshift;                              //< Green shift value
    uint8_t bshift;                              //< Blue shift value
    uint8_t *gamma;                              //< Gamma correction table
} ws2811_channel_t;

typedef struct
{
    uint64_t render_wait_time;                   //< time in µs before the next render can run
    struct ws2811_device *device;                //< Private data for driver use
    struct rpi_hw_t *rpi_hw;                     //< RPI Hardware Information
    uint32_t freq;                               //< Required output frequency
    int dmanum;                                  //< DMA number _not_ already in use
    ws2811_channel_t channel[RPI_PWM_CHANNELS];
} ws2811_t;


int ws2811_init(ws2811_t *ws2811);
void ws2811_fini(ws2811_t *ws2811);
int ws2811_render(ws2811_t *ws2811);
int ws2811_wait(ws2811_t *ws2811);
""")
ws = ffi.dlopen("./libws2811.so")

# LED configuration.
LED_FREQ_HZ    = 800000     # Frequency of the LED signal.  Should be 800khz or 400khz.
LED_DMA_NUM    = 10         # DMA channel to use, can be 0-14.
LED_GPIO       = 12         # GPIO physical pin connected to the LED signal line.  Must support PWM!
LED_INVERT     = 0          # Set to 1 to invert the LED signal, good if using NPN
                            # transistor as a 3.3V->5V level converter.  Keep at 0
                            # for a normal/non-inverted signal.

class ws2811_t:


    def __init__(self, count, freq=LED_FREQ_HZ, dmanum=LED_DMA_NUM, gpionum=LED_GPIO, invert=LED_INVERT, clearonexit=True):
        self.leds = None
        self.clearonexit = clearonexit
        leds = ffi.new("ws2811_t *")
        self.setup(leds, count, freq, dmanum, gpionum, invert)
        rc = ws.ws2811_init(leds)
        if rc != 0:
            raise IOError(rc)
        self.leds = leds

    def __del__(self):
        if self.leds is not None and self.clearonexit:
            self.fill(0, 0)
            self.render()
            ws.ws2811_fini(self.leds)
            self.leds = None

    def setup(self, leds, count, freq=LED_FREQ_HZ, dmanum=LED_DMA_NUM, gpionum=LED_GPIO, invert=LED_INVERT):
        leds.freq = freq
        leds.dmanum = dmanum

        for i in range(2):
            leds.channel[i].gpionum = 0
            leds.channel[i].invert = 0
            leds.channel[i].brightness = 0xff
            leds.channel[i].count = 0
            leds.channel[i].strip_type = WS2811_STRIP_RGB
        leds.channel[0].gpionum = gpionum
        leds.channel[0].invert = invert
        leds.channel[0].brightness = 0xff
        leds.channel[0].count = count
        leds.channel[0].strip_type = WS2811_STRIP_RGB

    def info(self):
        print('''
time in µs before the next render can run..................={0}\n\
Required output frequency..................................={1}\n\
DMA number _not_ already in use............................={2}\n\
'''.format(
    self.leds.render_wait_time,
    self.leds.freq,
    self.leds.dmanum,
))
        for i in range(2):
            if not self.leds.channel[i].gpionum:
                continue
            print('''
Channel....................................................={0}\n\
GPIO Pin with PWM alternate function, 0 if unused..........={1}\n\
Invert output signal.......................................={2}\n\
Number of LEDs, 0 if channel is unused.....................={3}\n\
Strip color layout -- one of WS2811_STRIP_xxx constants....={4:08x}\n\
Brightness value between 0 and 255.........................={5}\n\
White shift value..........................................={6}\n\
Red shift value............................................={7}\n\
Green shift value..........................................={8}\n\
Blue shift value...........................................={9}\n\
'''.format(
    i,
    self.leds.channel[i].gpionum,
    self.leds.channel[i].invert,
    self.leds.channel[i].count,
    self.leds.channel[i].strip_type,
    self.leds.channel[i].brightness,
    self.leds.channel[i].wshift,
    self.leds.channel[i].rshift,
    self.leds.channel[i].gshift,
    self.leds.channel[i].bshift,
))
            leds = self.leds.channel[i].leds
            for j in range(1, self.leds.channel[i].count+1):
                print('%08x'%leds[j-1], end=',')
                if j and j%10 == 0:
                    print()
            print()

    def fill(self, channel, rgb):
        leds = self.leds.channel[channel].leds
        for i in range(self.leds.channel[channel].count):
            leds[i] = rgb

    def __setitem__(self, led, rgb):
        self.leds.channel[0].leds[led] = rgb

    def __getitem__(self, led):
        return self.leds.channel[0].leds[led]

    def render(self):
        return ws.ws2811_render(self.leds)

def main():
    dotcolors = [
        0x00200000,  # red
        0x00201000,  # orange
        0x00202000,  # yellow
        0x00002000,  # green
        0x00002020,  # lightblue
        0x00000020,  # blue
        0x00100010,  # purple
        0x00200010,  # pink
    ]
    leds = ws2811_t(30*5//3) # 30leds/m * 5m / 3leds/chip
    leds.info()
    try:
        for rgb in dotcolors:
            leds.fill(0, rgb)
            leds[50-5] = 0
            leds.render()
            time.sleep(0.5)
    finally:
        #del leds
        print('done')

if __name__ == '__main__':
    main()
