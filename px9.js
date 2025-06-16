!function(w){
    var cache = null;
    
    function process(raw, secret) {
        var out = '';
        var data = toArray(raw);
        var keylen = secret.length;
        
        for (var i = 0; i < data.length; i++) {
            out += String.fromCharCode(data[i] ^ secret.charCodeAt(i % keylen));
        }
        
        return out;
    }
    
    function toArray(str) {
        var bytes = new Uint8Array(str.length / 2);
        for (var i = 0; i < str.length; i += 2) {
            bytes[i / 2] = parseInt(str.substr(i, 2), 16);
        }
        return bytes;
    }
    
    function extract(idx) {
        if (!cache) {
            prepare();
        }
        
        if (!cache || !cache[idx]) {
            return null;
        }
        
        return cache[idx].content;
    }
    
    function prepare() {
        var secret = atob(w._m.r);
        
        cache = [];
        
        var count = w._t.l;
        
        for (var i = 0; i < count; i++) {
            var chunks = w['_p' + i];
            
            var seqRaw = w._s[i];
            var seq = JSON.parse(process(seqRaw, secret));
            
            var decrypted = chunks.map(function(chunk) {
                return process(chunk, secret);
            });
            
            var arranged = [];
            for (var j = 0; j < seq.length; j++) {
                arranged[seq[j]] = decrypted[j];
            }
            
            var final = arranged.join('');
            
            cache[i] = {
                content: final,
                auth: w._a[i]
            };
        }
    }
    
    function access(evt) {
        evt.preventDefault();
        
        var idx = parseInt(this.getAttribute('data-index'), 10);
        
        var resource = extract(idx);
        
        if (resource) {
            var win = w.open(resource, '_blank');
            if (win) {
                win.focus();
            }
        }
    }
    
    function setup() {
        document.querySelectorAll('.download-link').forEach(function(btn) {
            btn.addEventListener('click', access);
        });
        
        setTimeout(function() {
            w.__sys = function() {};
        }, 1200);
    }
    
    document.addEventListener('DOMContentLoaded', setup);
}(window);