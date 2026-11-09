"""Keep work on the input thread proportional to visible or changed state."""
from types import SimpleNamespace

from src.live.desktop import DesktopApp
from src.live.category_browser import CategoryBrowser
from src.live.panel import CompactPanel


def test_idle_confirmation_does_not_read_catalog_or_touch_widgets():
    class NoCatalog:
        def __iter__(self):raise AssertionError('Full catalog scan on UI timer')
    app=SimpleNamespace(session=SimpleNamespace(items=NoCatalog(),pending_ids=set()),pending_order=[])
    DesktopApp.sync_pending_candidates(app)


def test_confirmation_updates_only_changed_candidates_and_clears_once():
    calls=[];lookups=[]
    item=SimpleNamespace(id='marker:123',name='Baú')
    def lookup(identifier):lookups.append(identifier);return item
    class Widget:
        def configure(self,**kwargs):calls.append(kwargs)
        def set(self,value):calls.append(('set',value))
        def pack(self,**kwargs):calls.append('show')
        def pack_forget(self):calls.append('hide')
    app=SimpleNamespace(session=SimpleNamespace(pending_ids={'marker:123'},item_by_id=lookup),
                        pending_order=[],candidates=Widget(),confirm_button=Widget())
    DesktopApp.sync_pending_candidates(app)
    before=list(calls)
    DesktopApp.sync_pending_candidates(app)
    assert calls==before and lookups==['marker:123']
    app.session.pending_ids.clear();DesktopApp.sync_pending_candidates(app)
    assert calls[-2:]==['hide','hide'] and app.pending_order==[]


def test_hidden_category_list_never_schedules_redraw_and_visible_click_is_immediate():
    calls=[]
    browser=SimpleNamespace(paint_job=None,winfo_ismapped=lambda:False,
        after=lambda delay,callback:calls.append(delay) or 'job',paint=lambda:None)
    CategoryBrowser.schedule_paint(browser);assert calls==[]
    browser.winfo_ismapped=lambda:True
    CategoryBrowser.schedule_paint(browser);CategoryBrowser.schedule_paint(browser)
    assert calls==[0]


def test_search_coalesces_rapid_typing_before_rebuilding_rows():
    scheduled={};cancelled=[];queries=[]
    class Root:
        def after(self,delay,callback):
            key=len(scheduled);scheduled[key]=callback;return key
        def after_cancel(self,key):cancelled.append(key)
    query=['m']
    app=SimpleNamespace(root=Root(),category_query=SimpleNamespace(get=lambda:query[0]),
        category_browser=SimpleNamespace(filter=queries.append))
    CompactPanel.filter_categories(app);query[0]='menta';CompactPanel.filter_categories(app)
    assert queries==[] and cancelled==[0]
    scheduled[1]();assert queries==['menta'] and app.category_filter_job is None
