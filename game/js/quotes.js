// Whimsy quote of the day — one per calendar day, same for everyone.
// Original lines written for Dreamhouse Kingdom. 💖

export const QUOTES = [
  'You are the main character — the plot is just warming up.',
  'Sparkle like nobody is refreshing their feed.',
  'Dreams do not have expiration dates, babe.',
  'Wear the tiara to the grocery store of life.',
  'Your softness is not a weakness; it is a superpower in a pink cardigan.',
  'Today is giving fresh start energy. Take it.',
  'Butterflies in your tummy are just dreams doing cartwheels.',
  'Be the disco ball: broken into a million pieces and still throwing light everywhere.',
  'A little glitter fixes almost everything. For the rest, there is a nap.',
  'Manifest loudly. The universe has headphones in.',
  'You were not made to fit in a lunchbox category, cupcake.',
  'Some days you slay the dragon, some days you just braid its hair. Both count.',
  'Romanticize the small stuff: the latte, the playlist, the walk home.',
  'Your comfort zone called — it misses you, but it will understand.',
  'Every queen was once a girl who decided to keep going.',
  'Doubt is just a bad wifi signal between you and your dreams. Move closer.',
  'Bloom anyway. The garden was never asking for permission.',
  'The glass slipper fits better when you walk your own pace.',
  'Keep your standards high and your ponytail higher.',
  'You are one deep breath away from main-character calm.',
  'Trust the glow-up in progress — buffering is part of the magic.',
  'Star quality is 10% shine and 90% showing up.',
  'If the crown feels heavy, take a snack break. Queens snack.',
  'Write your to-do list in gel pen; make destiny fun again.',
  'Even the moon has phases. You are allowed to have them too.',
  'Talk to yourself like you talk to your best friend at 2am.',
  'The magic mirror says: you, specifically, are doing great.',
  'Wish on stars, but pack your own sparkle just in case.',
  'Your era is not coming — it is already here, doing sound check.',
  'Kindness is the ultimate Y2K accessory. Never goes out of style.',
  'Plot twist: the fairy godmother was your own tiny brave decisions.',
  'Dance like the CD never skips.',
  'Grow through it, glitter through it, giggle through it.',
  'You are the limited edition. There is no restock.',
  'Small steps in cute shoes still cover miles.',
  'Let them wonder how you keep glowing. (It is water, sleep, and audacity.)',
  'Happily ever after is a direction, not a deadline.',
  'Your heart is a dreamhouse — keep the lights on.',
  'Be curious like a kitten in a castle.',
  'The fairytale is not the prince. The fairytale is you, becoming.',
];

// Deterministic pick: same quote for the whole day, changes at midnight.
export function quoteOfTheDay(date = new Date()) {
  const dayIndex = Math.floor(
    (date.getTime() - date.getTimezoneOffset() * 60000) / 86400000
  );
  return QUOTES[((dayIndex % QUOTES.length) + QUOTES.length) % QUOTES.length];
}

export function todayKey(date = new Date()) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}
