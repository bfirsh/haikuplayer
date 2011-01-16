from appscript import *
import time

shows = [
    ('b00xjy01', 11, 11, 1.5),
    ('b00p99px', 1, 4, 2),
]

safari = app('safari')
doc = safari.make(new=k.document)
window = safari.windows()[0]
current_tab = None

for pid, mins, secs, duration in shows:
    if current_tab is None:
        current_tab = window.tabs()[0]
    else:
        current_tab = window.make(new=k.tab)
        window.current_tab.set(current_tab)
    current_tab.URL.set('http://www.bbc.co.uk/iplayer/episode/%s' % pid)
    # Wait until redirected to full URL
    while True:
        try:
            url = current_tab.URL()
        except IndexError:
            pass
        else:
            if 'bbc.co.uk' in url and not url.endswith(pid):
                break
        time.sleep(0.1)
    current_tab.URL.set('%s?t=%sm%ss' % (url, mins, secs))
    time.sleep(0.5)
    current_tab.do_JavaScript("""
        var Python = {
            pauseOnLoad: function() {
                if (iplayer && iplayer.models.Emp.getInstance().isPlaying()) {
                    Python.emp = iplayer.models.Emp.getInstance();
                    Python.emp.pause();
                    clearInterval(Python.pauseOnLoadInterval);
                }
            }
        };
        Python.pauseOnLoadInterval = setInterval(Python.pauseOnLoad, 100);
    """)

# Wait for this flash player to load
time.sleep(1)

tabs = window.tabs()

# Spin through all the tabs backwards to load the flash players
for tab in reversed(tabs):
    window.current_tab.set(tab)

raw_input('Press enter to start playback')

for i, (pid, mins, secs, duration) in enumerate(shows):
    print "Playing tab %s..." % i
    window.current_tab.set(tabs[i])
    tabs[i].do_JavaScript('Python.emp.play();')
    time.sleep(duration+0.25)
    tabs[i].do_JavaScript('Python.emp.pause();')




