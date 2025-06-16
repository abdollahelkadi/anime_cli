    function redirectToLink(encodedUrl) {
        var decodedUrl = atob(encodedUrl);
        window.location.href = decodedUrl;
    }


function openEpisode(encodedPermalink) {
var decodedPermalink = atob(encodedPermalink);
window.location.href = decodedPermalink;
}