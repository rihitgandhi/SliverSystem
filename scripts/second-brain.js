(() => {
  'use strict';

  document.querySelectorAll('.demo-player[data-video-id]').forEach((player) => {
    const button = player.querySelector('.demo-play');
    if (!button) return;

    button.addEventListener('click', () => {
      const videoId = player.dataset.videoId;
      if (!videoId) return;

      const frame = document.createElement('iframe');
      frame.src = `https://www.youtube-nocookie.com/embed/${encodeURIComponent(videoId)}?autoplay=1&rel=0`;
      frame.title = 'Second Brain product demo';
      frame.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share';
      frame.allowFullscreen = true;
      player.replaceChildren(frame);
    }, { once: true });
  });
})();
