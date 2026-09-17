"""Page HTML de l'onglet controle (WASD + live feed)."""

_PAGE_HTML = """<!doctype html>
<html lang='fr'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>Roover Mk1 - Controle manuel</title>
<style>
  body { margin: 0; font-family: Segoe UI, Arial, sans-serif;
         background: linear-gradient(180deg, #eef6fb, #ddeaf4); color:#234; }
  header { background:#3a6ea5; color:white; padding:1rem; }
  header h1 { margin:0; font-size:1.4rem; }
  .layout { display:flex; gap:1.5rem; padding:1.5rem; flex-wrap:wrap; }
  .video-pane, .control-pane { background:white; border-radius:10px;
                               box-shadow:0 2px 6px rgba(0,0,0,0.08);
                               padding:1rem; }
  .video-pane { flex:2 1 480px; min-width:320px; }
  .control-pane { flex:1 1 280px; min-width:240px; }
  img.video { width:100%; max-width:640px; border:1px solid #cfd9e2;
              border-radius:6px; background:#000; display:block; }
  .status { font-family: monospace; background:#f3f7fb; padding:0.5rem;
            border-radius:6px; min-height:1.2em; }
  button { padding:0.6rem 1rem; margin:0.2rem 0; border:none;
           border-radius:6px; background:#3a6ea5; color:white;
           cursor:pointer; font-size:1rem; }
  button:hover { background:#2c5780; }
  button.danger { background:#aa3939; }
  button.danger:hover { background:#883030; }
  .wasd-grid { display:grid; grid-template-columns: repeat(3, 3rem);
               grid-template-rows: repeat(2, 3rem); gap:0.4rem;
               justify-content:center; margin:1rem 0; }
  .wasd-grid .key { background:#cfd9e2; border-radius:6px;
                    display:flex; align-items:center; justify-content:center;
                    font-weight:bold; font-family:monospace; font-size:1.2rem;
                    user-select:none; }
  .wasd-grid .key.active { background:#3a6ea5; color:white; }
  .key-w { grid-column:2; grid-row:1; }
  .key-a { grid-column:1; grid-row:2; }
  .key-s { grid-column:2; grid-row:2; }
  .key-d { grid-column:3; grid-row:2; }
  .key-q { grid-column:1; grid-row:1; }
  .key-e { grid-column:3; grid-row:1; }
  p.hint { color:#567; font-size:0.9rem; }
</style>
</head>
<body>
<header><h1>Roover Mk1 - Controle manuel (WASD)</h1></header>
<div class='layout'>
  <div class='video-pane'>
    <img class='video' src='/video' alt='Flux camera'>
  </div>
  <div class='control-pane'>
    <button id='btnStart'>Activer controle manuel</button>
    <button id='btnStop' class='danger'>Desactiver / Arret</button>
    <p class='hint'>Active le controleur, puis utilise <b>W A S D</b> sur le clavier.</p>
    <div class='wasd-grid'>
      <div class='key key-w' id='keyW'>W</div>
      <div class='key key-a' id='keyA'>A</div>
      <div class='key key-s' id='keyS'>S</div>
      <div class='key key-d' id='keyD'>D</div>
      <div class='key key-q' id='keyQ'>Q</div>
      <div class='key key-e' id='keyE'>E</div>
    </div>
    <div class='status' id='status'>Inactif</div>
  </div>
</div>

<script>
(function() {
  var held = { w:false, a:false, s:false, d:false, q:false, e:false };
  var sendInterval = null;
  var statusEl = document.getElementById('status');

  function refreshKeys() {
    ['w','a','s','d','q','e'].forEach(function(k) {
      var el = document.getElementById('key' + k.toUpperCase());
      if (held[k]) { el.classList.add('active'); }
      else { el.classList.remove('active'); }
    });
  }

  function sendKeys() {
    var keys = Object.keys(held).filter(function(k) { return held[k]; });
    fetch('/control/keys', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ keys: keys })
    }).catch(function(e) { console.error('keys POST:', e); });
  }

  function startPolling() {
    if (sendInterval) return;
    sendKeys();
    sendInterval = setInterval(sendKeys, 80);
  }

  function stopPolling() {
    if (sendInterval) { clearInterval(sendInterval); sendInterval = null; }
    held = { w:false, a:false, s:false, d:false, q:false, e:false };
    refreshKeys();
    fetch('/control/stop', { method: 'POST' }).catch(function() {});
  }

  function isWasd(k) { return ['w','a','s','d','q','e'].indexOf(k) >= 0; }

  document.addEventListener('keydown', function(e) {
    var k = (e.key || '').toLowerCase();
    if (!isWasd(k)) return;
    if (e.repeat) return;
    held[k] = true;
    refreshKeys();
    startPolling();
  });

  document.addEventListener('keyup', function(e) {
    var k = (e.key || '').toLowerCase();
    if (!isWasd(k)) return;
    held[k] = false;
    refreshKeys();
    var any = held.w || held.a || held.s || held.d || held.q || held.e;
    if (any) { sendKeys(); } else { stopPolling(); }
  });

  window.addEventListener('blur', stopPolling);

  document.getElementById('btnStart').addEventListener('click', function() {
    fetch('/controller/start_manual', { method: 'POST' })
      .then(function(r) { return r.json(); })
      .then(function(j) { statusEl.textContent = JSON.stringify(j); })
      .catch(function(e) { statusEl.textContent = 'erreur: ' + e; });
  });

  document.getElementById('btnStop').addEventListener('click', function() {
    stopPolling();
    fetch('/controller/stop', { method: 'POST' })
      .then(function(r) { return r.json(); })
      .then(function(j) { statusEl.textContent = JSON.stringify(j); })
      .catch(function(e) { statusEl.textContent = 'erreur: ' + e; });
  });

  setInterval(function() {
    fetch('/controller/status').then(function(r) { return r.json(); })
      .then(function(j) {
        if (!j.active) {
          statusEl.textContent = 'Inactif';
        } else {
          statusEl.textContent = j.name + '  L=' + j.left_speed + ' R=' + j.right_speed;
        }
      }).catch(function() {});
  }, 500);
})();
</script>
</body>
</html>
"""


def render_control_tab():
    """Retourne la page HTML de l'onglet controle."""

    return _PAGE_HTML
