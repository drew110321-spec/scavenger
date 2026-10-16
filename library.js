// The games in the Games app live here. Add one like this:
//
//   {
//     title: "Snake",                    // required
//     url: "games/snake/index.html",     // required: a page inside this folder, or a full https:// link
//     image: "icons/snake.svg",          // optional: icon picture
//     description: "Classic snake"       // optional: shown in search results
//   },
//
// A game needs to be PLAYABLE at the url: a page in this folder, or a full web
// link (like a GitHub Pages site). Some outside sites refuse to load inside
// another site; for those, use the open-in-new-tab button in the title bar.
//
// The AI app has its own built-in assistants, so nothing for it goes here.
//
// aiKey: a Gemini API key put here is SHARED BY EVERY DEVICE that opens this
// site, so no one has to type one in. Get a free key at
// https://aistudio.google.com/apikey and paste it between the quotes.
//   - Anyone who opens the page's source can read this key, so use a free key
//     you can replace, and keep this site's files private if you can.
//   - Leave it "" to instead have each person enter their own key per device.
//   - A person can still set their own key on their device, which overrides this.

window.LIBRARY = {
  siteName: "Nebula",

  // Base64-obfuscated so the raw key isn't plain text in the file (decoded at
  // runtime by decodeBuiltin in ai.js). Obfuscation is a speed bump, not real
  // secrecy — anyone determined can still decode it, so rotate the key if abused.
  aiKey: "QVEuQWI4Uk42TFRzT0xhZkN4MmpzeUhnYXBvUGpyVk1fSzU3ckxJQVRENEVrNDg4ZUhQYUE=",

  games: [
    { title: "ORBIT", url: "orbit/index.html", image: "icons/orbit.svg" }
  ]
};
