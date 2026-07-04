// Trivia content for Dreamhouse Kingdom — 5 zones x 3 questions.
// Themed: old Barbie glam x Y2K pop culture x classic Disney nostalgia.
// Each question: { q, options[], answer (index) }

export const ZONES = [
  {
    id: 'cafe',
    name: 'Café Coquette',
    emoji: '🧁',
    color: 0xffb7d9,
    accent: '#ff8fc4',
    topic: 'Sweet Treats',
    questions: [
      {
        q: 'Which French dessert is made of two delicate almond-meringue shells with a creamy filling?',
        options: ['Macaron', 'Éclair', 'Crêpe', 'Croissant'],
        answer: 0,
      },
      {
        q: 'What coffee order is espresso topped with steamed milk and a thick cloud of foam?',
        options: ['Americano', 'Cappuccino', 'Cold brew', 'Ristretto'],
        answer: 1,
      },
      {
        q: 'Matcha, the star of every aesthetic café menu, is a powdered form of…',
        options: ['Vanilla bean', 'Chamomile', 'Green tea leaves', 'Pistachio'],
        answer: 2,
      },
    ],
  },
  {
    id: 'boutique',
    name: 'Dream Boutique',
    emoji: '👗',
    color: 0xff5fa8,
    accent: '#ff2d95',
    topic: 'Doll-core Fashion',
    questions: [
      {
        q: 'Which signature color has been Barbie’s whole aesthetic since forever?',
        options: ['Lavender', 'Red', 'Pink', 'Turquoise'],
        answer: 2,
      },
      {
        q: 'Butterfly clips, frosted lip gloss and rhinestone everything scream which fashion era?',
        options: ['The Y2K era', 'The disco 70s', 'The roaring 20s', 'The grunge 90s'],
        answer: 0,
      },
      {
        q: 'Which iconic designer made the “little black dress” a forever wardrobe staple?',
        options: ['Donatella Versace', 'Coco Chanel', 'Vera Wang', 'Miuccia Prada'],
        answer: 1,
      },
    ],
  },
  {
    id: 'glow',
    name: 'The Glow Bar',
    emoji: '💄',
    color: 0xffc9a8,
    accent: '#ff9f70',
    topic: 'Beauty',
    questions: [
      {
        q: 'What does the SPF on your sunscreen actually stand for?',
        options: ['Skin Perfecting Formula', 'Sun Protection Factor', 'Solar Particle Filter', 'Sun Prevention Force'],
        answer: 1,
      },
      {
        q: 'Which beloved K-beauty step involves relaxing under a sheet soaked in essence?',
        options: ['Double cleanse', 'Gua sha', 'Sheet mask', 'Slugging'],
        answer: 2,
      },
      {
        q: 'Hyaluronic acid is a skincare sweetheart because it…',
        options: ['Exfoliates dead skin', 'Attracts and holds moisture', 'Blocks UV rays', 'Dissolves makeup'],
        answer: 1,
      },
    ],
  },
  {
    id: 'stage',
    name: 'Pop Star Stage',
    emoji: '🎤',
    color: 0xa8ecc9,
    accent: '#3ecf8e',
    topic: 'Y2K Pop',
    questions: [
      {
        q: 'Who burst onto the scene in 1998 singing “…Baby One More Time”?',
        options: ['Christina Aguilera', 'Britney Spears', 'Mandy Moore', 'Jessica Simpson'],
        answer: 1,
      },
      {
        q: 'Which girl group told us what they really, really want in the hit “Wannabe”?',
        options: ['Destiny’s Child', 'Little Mix', 'TLC', 'Spice Girls'],
        answer: 3,
      },
      {
        q: 'Which beloved Y2K keychain gadget let you raise a tiny digital pet?',
        options: ['Game Boy', 'Furby', 'Tamagotchi', 'Walkman'],
        answer: 2,
      },
    ],
  },
  {
    id: 'garden',
    name: 'Once Upon a Garden',
    emoji: '🏰',
    color: 0xcbb2ff,
    accent: '#a98bf5',
    topic: 'Storybook Classics',
    questions: [
      {
        q: 'In the classic Cinderella story, what does she leave behind on the palace steps?',
        options: ['Her tiara', 'A glass slipper', 'Her invitation', 'A silk glove'],
        answer: 1,
      },
      {
        q: 'Which little mermaid dreams of the human world while singing “Part of Your World”?',
        options: ['Aurora', 'Belle', 'Ariel', 'Jasmine'],
        answer: 2,
      },
      {
        q: 'In The Lion King (1994), which cheerful phrase means “no worries”?',
        options: ['Hakuna Matata', 'Bibbidi-Bobbidi-Boo', 'Circle of Life', 'Ohana'],
        answer: 0,
      },
    ],
  },
];

export const TOTAL_QUESTIONS = ZONES.reduce((n, z) => n + z.questions.length, 0);
