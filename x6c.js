(function() {
    var _m1 = "7350", _m2 = "3d58-f228-", _m3 = "425f-97f1-", _m4 = "2d9512f5772c";
    var FRAMEWORK_HASH = "";
    
    function initializeLayout() {
        var primaryElement = document.querySelector("#episode-servers li:first-child a");
        if (primaryElement) {
            renderModuleContent(primaryElement);
        }
        displayModuleOptions();
    }
    
    function renderModuleContent(elementNode) {
        var moduleKey = elementNode.getAttribute("data-server-id");
        var resourceData = window.resourceRegistry[moduleKey];
        var configSettings = window.configRegistry[moduleKey];
        
        if (resourceData && configSettings) {
            if (!FRAMEWORK_HASH) {
                FRAMEWORK_HASH = _m1 + _m2 + _m3 + _m4;
                _m1 = _m2 = _m3 = _m4 = null;
            }
            
            resourceData = resourceData.split('').reverse().join('');
            resourceData = resourceData.replace(/[^A-Za-z0-9+/=]/g, '');
            
            var paramOffset = getParameterOffset(configSettings);
            var decodedResource = atob(resourceData).slice(0, -paramOffset);
            
            var resourcePattern = /^https:\/\/yonaplay\.org\/embed\.php\?id=\d+$/;
            var resolvedResource = resourcePattern.test(decodedResource) ? 
                decodedResource + "&apiKey=" + FRAMEWORK_HASH : decodedResource;
            
            var contentContainer = document.getElementById("iframe-container");
            var overlayElement = document.getElementById("play-button-container");
            
            if (overlayElement) {
                overlayElement.style.display = "none";
            }
            
            contentContainer.innerHTML = "";
            
            var contentFrame = document.createElement("iframe");
            contentFrame.width = "100%";
            contentFrame.height = "100%";
            contentFrame.src = resolvedResource;
            contentFrame.frameBorder = "0";
            contentFrame.allowFullscreen = true;
            
            var restrictedDomains = ["videa.hu", "www.yourupload.com", "www.mp4upload.com"];
            var resourceDomain;
            
            try {
                resourceDomain = new URL(resolvedResource).hostname;
                
                if (restrictedDomains.includes(resourceDomain)) {
                    contentFrame.setAttribute("sandbox", "allow-scripts allow-same-origin");
                }
            } catch(e) {}
            
            contentContainer.appendChild(contentFrame);
            
            var activeModules = document.querySelectorAll("#episode-servers li.active");
            activeModules.forEach(function(module) {
                module.classList.remove("active");
            });
            
            elementNode.parentElement.classList.add("active");
        }
    }
    
    function getParameterOffset(configSettings) {
        var indexKey = atob(configSettings.k);
        return configSettings.d[parseInt(indexKey, 10)];
    }
    
    function registerModuleListeners() {
        var moduleSelectors = document.querySelectorAll("#episode-servers a");
        moduleSelectors.forEach(function(selector) {
            selector.addEventListener("click", function(event) {
                event.preventDefault();
                renderModuleContent(this);
            });
        });
    }
    
    function displayModuleOptions() {
        var optionsContainer = document.getElementById("episode-servers");
        if (optionsContainer) {
            optionsContainer.style.display = "block";
        }
    }
    
    function init() {
        var controlElement = document.getElementById("play-button-container");
        if (controlElement) {
            controlElement.addEventListener("click", initializeLayout);
        }
        
        var optionsContainer = document.getElementById("episode-servers");
        if (optionsContainer) {
            optionsContainer.style.display = "none";
        }
        
        registerModuleListeners();
    }
    
    window.init = init;
    
    window.loadIframe = function(element) {
        renderModuleContent(element);
    };
    
    document.addEventListener("DOMContentLoaded", init);
})();