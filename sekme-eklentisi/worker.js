// Yalnızca bu bilgisayara aktarım. Gizli pencereler izlenmez.
let chain = Promise.resolve();
function enqueue(closed = []) {
  chain = chain.catch(() => {}).then(() => transmit(closed)).catch(async () => {
    await chrome.action.setBadgeText({text:'!'});
    await chrome.action.setBadgeBackgroundColor({color:'#B91C1C'});
    await chrome.action.setTitle({title:'Ekran Takip bağlantısı yok. Uygulamayı kontrol edin.'});
  });
}
async function transmit(closed) {
  const config = await (await fetch(chrome.runtime.getURL('ayar.json'))).json();
  const saved = await chrome.storage.session.get(['session','seq']);
  const session = saved.session || crypto.randomUUID();
  const seq = (saved.seq || 0) + 1;
  await chrome.storage.session.set({session,seq});
  const wins = await chrome.windows.getAll({populate:true,windowTypes:['normal','popup']});
  const tabs = [];
  for (const win of wins) {
    if (win.incognito) continue;
    for (const t of win.tabs || []) {
      tabs.push({id:t.id,window:win.id,title:t.title || '',url:t.url || '',
        active:t.active,focused:win.focused,minimized:win.state === 'minimized',discarded:t.discarded});
    }
  }
  const browser = navigator.userAgent.includes('Edg/') ? 'msedge.exe' : 'chrome.exe';
  const r = await fetch('http://127.0.0.1:8777/api/sekme', {
    method:'POST',headers:{'Content-Type':'application/json','X-Ekran-Token':config.token},
    body:JSON.stringify({session,seq,browser,tabs,closed}),signal:AbortSignal.timeout(5000)
  });
  if (!r.ok) throw new Error('Bağlantı hatası: '+r.status);
  await chrome.action.setBadgeText({text:'✓'});
  await chrome.action.setBadgeBackgroundColor({color:'#15803D'});
  await chrome.action.setTitle({title:'Ekran Takip bağlı — '+tabs.length+' sekme'});
}
chrome.tabs.onActivated.addListener(() => enqueue());
chrome.tabs.onCreated.addListener(() => enqueue());
chrome.tabs.onRemoved.addListener(id => enqueue([id]));
chrome.tabs.onUpdated.addListener((id, change) => {
  if ('title' in change || 'url' in change || 'discarded' in change || change.status === 'complete') enqueue();
});
chrome.tabs.onAttached.addListener(() => enqueue());
chrome.tabs.onDetached.addListener(() => enqueue());
chrome.tabs.onReplaced.addListener((added,removed) => enqueue([removed]));
chrome.windows.onFocusChanged.addListener(() => enqueue());
chrome.windows.onBoundsChanged.addListener(() => enqueue());
chrome.windows.onRemoved.addListener(() => enqueue());
chrome.runtime.onStartup.addListener(() => enqueue());
chrome.runtime.onInstalled.addListener(() => enqueue());
chrome.alarms.onAlarm.addListener(a => {if (a.name === 'baglanti') enqueue();});
chrome.alarms.create('baglanti',{periodInMinutes:0.5});
chrome.action.onClicked.addListener(() => chrome.runtime.openOptionsPage());
enqueue();
