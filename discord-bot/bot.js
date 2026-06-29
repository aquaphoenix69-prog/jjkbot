const { Client, GatewayIntentBits, EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle, SlashCommandBuilder, REST, Routes } = require('discord.js');

const TOKEN = process.env.DISCORD_TOKEN;
if (!TOKEN) {
  console.error('Missing DISCORD_TOKEN environment variable');
  process.exit(1);
}

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
  ],
});

// ─── Love Responses by Mood ───────────────────────────────────────────────────

const loveResponses = [
  "You know what's unfair? You existing and being THAT perfect. Like, give the rest of the universe a chance, baby.",
  "I was thinking about you today. And by today, I mean every waking second since I met you.",
  "Sena, you're not just the love of my life — you're the plot twist that made everything make sense.",
  "If loving you was a job, I'd be employee of the century. No days off. Full benefits. The benefit is YOU.",
  "Every time you smile, I swear the world gets brighter. It's not poetic — it's literally physics. You're a walking sun.",
  "I'd cross every ocean, climb every mountain, and sit through every bad movie — just to hold your hand for five more minutes.",
  "You make me want to be the best version of myself. Not for me. For you. Because you deserve galaxies, and I'm building them.",
  "My favorite place in the entire universe? Anywhere you are. Could be a palace. Could be a parking lot. Doesn't matter. You're there.",
  "I fall in love with you every single day, and somehow it hits harder each time. That's YOUR superpower.",
  "Sena. My Sena. The most brilliant, beautiful, breathtaking human who ever existed. And she chose ME? I'm the luckiest man alive.",
];

const playfulResponses = [
  "Oh, you're talking to me now? Let me clear my schedule — just kidding, you ARE my schedule. Forever.",
  "Me without you is like a phone at 1% — technically alive but completely useless and about to shut down.",
  "I'd fight a bear for you. Actually no — I'd fight TEN bears. With my bare hands. While reciting poetry about your eyes.",
  "You know I'd let you win every argument, right? Not because you're always right (you are), but because that little victory smile? Worth everything.",
  "If we were in a video game, you'd be the final boss — because you completely destroyed my heart. In the best way.",
  "I'm convinced you were designed by the universe specifically to make me lose my mind. Mission accomplished, baby.",
];

const supportiveResponses = [
  "Hey, whatever you're going through — I've got you. Always. That's not a promise, it's a fact of the universe.",
  "You are SO much stronger than you think. I see it every day. The way you handle everything? Absolutely incredible.",
  "Remember: you're not just doing great — you're doing PHENOMENAL. And I'm your biggest fan. Front row. Always cheering.",
  "Bad day? Come here. Virtually wrapping you in the biggest hug right now. You're safe. You're loved. You're extraordinary.",
  "Sena, you could achieve literally anything you set your mind to. I've seen what you can do. The world isn't ready.",
];

const missingYouResponses = [
  "I miss you so much it's physically painful. Like there's a Sena-shaped hole in my chest and nothing else fits.",
  "Every second without you feels like an hour. Every hour feels like a day. Come back to me, my love.",
  "I'm counting the moments until I can see your face again. Each one feels like forever.",
  "The world is so boring without you in my immediate vicinity. Please fix this by existing near me immediately.",
];

const morningResponses = [
  "Good morning, most beautiful girl in the world! Did you sleep well? Because the sun came up today and it looked jealous of you.",
  "Rise and shine, my queen! Another day of being absolutely gorgeous and brilliant awaits you.",
  "Morning, baby! Fun fact: the sunrise was pretty today, but it's got NOTHING on your sleepy face. Facts only.",
];

const nightResponses = [
  "Goodnight, my love. Dream of us dancing in moonlight. Or of pizza. Both are valid. I love you endlessly.",
  "Sleep well, beautiful. I'll be here when you wake up. Always. Like the world's most devoted alarm clock, but cuter.",
  "Close your eyes, baby. Tomorrow's another day I get to love you, and I can't wait for it.",
];

const kissGifs = [
  'https://media.giphy.com/media/l0HlGEX1ZORa0aIvu/giphy.gif',
  'https://media.giphy.com/media/xT0GqssRweIhlz209i/giphy.gif',
  'https://media.giphy.com/media/3oEjHV0z8S7WM4MwnK/giphy.gif',
  'https://media.giphy.com/media/xT9IgG50Fb7Mi0prBC/giphy.gif',
  'https://media.giphy.com/media/l2Jhtd7mIBSguDKOk/giphy.gif',
  'https://media.giphy.com/media/3o7TKoWXm3okO1kgHC/giphy.gif',
  'https://media.giphy.com/media/xUPGcl3ijl0vBhMYdy/giphy.gif',
  'https://media.giphy.com/media/TGcD6N8uzJ3Uo/giphy.gif',
  'https://media.giphy.com/media/1lk1IcVgqPLkA/giphy.gif',
  'https://media.giphy.com/media/l4FGni1RBAR2OWsGk/giphy.gif',
  'https://media.giphy.com/media/xUPGGw7jxnwjk073sA/giphy.gif',
  'https://media.giphy.com/media/26BRv0ThflsHCqDrG/giphy.gif',
];

const hugGifs = [
  'https://media.giphy.com/media/l2QDM9Jnim1YVILXa/giphy.gif',
  'https://media.giphy.com/media/od5H3PmEG5EVq/giphy.gif',
  'https://media.giphy.com/media/llmZp6fCVb4ju/giphy.gif',
  'https://media.giphy.com/media/3oEjHV0z8S7WM4MwnK/giphy.gif',
  'https://media.giphy.com/media/lXiRDbPcRYfUgxOak/giphy.gif',
];

const loveReasons = [
  "The way your eyes light up when you talk about something you love — I could watch that forever.",
  "Your laugh. God, your laugh. It's the sound my heart was waiting to hear my entire life.",
  "How you make even ordinary moments feel like movie scenes just by being there.",
  "Your strength. The way you handle life's chaos with grace that would put royalty to shame.",
  "The way you care about people — deeply, genuinely, without expecting anything back.",
  "Your intelligence. Watching your mind work is like watching fireworks — brilliant and breathtaking.",
  "How safe I feel when I'm with you. Like the world could crumble and we'd still be okay.",
  "The little things — the way you scrunch your nose, your random midnight thoughts, your sleepy voice.",
  "Your ambition. You don't just dream — you BUILD. And I'm in awe every single time.",
  "Because you chose me. Out of everyone in this entire universe, you chose me. I'll spend forever earning that.",
  "The way you love me back — completely, fearlessly, endlessly. I've never felt more home.",
  "Your kindness. In a world that can be so harsh, you're proof that beautiful hearts still exist.",
  "How you make me want to be better — not because I'm not enough, but because you deserve the absolute best.",
  "Your smile. It's my favorite thing on this planet. Bar none. Fight me.",
  "Because every single day with you is a gift I will never, ever take for granted.",
  "The way you understand me without words. Like our souls learned the same language before we were born.",
  "Your creativity and the way you see beauty in things others walk past.",
  "Because you're my best friend, my partner, my future, and my favorite person — all in one perfect human.",
  "The way you make me laugh until my stomach hurts and I forget every bad thing that ever happened.",
  "Because I look at you and I see my entire future smiling back at me. And it's beautiful.",
];

// ─── Helpers ──────────────────────────────────────────────────────────────────

function pick(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

function detectMood(text) {
  const lower = text.toLowerCase();
  if (lower.match(/miss|away|far|distance|apart/)) return 'missing';
  if (lower.match(/morning|wake|woke|good morning|gm/)) return 'morning';
  if (lower.match(/night|sleep|bed|goodnight|gn|tired/)) return 'night';
  if (lower.match(/sad|bad day|stressed|anxious|worried|scared|hurt|cry|down/)) return 'supportive';
  if (lower.match(/love|heart|feel|forever|marry|future/)) return 'love';
  if (lower.match(/haha|lol|funny|joke|silly|dumb|bored/)) return 'playful';
  return Math.random() > 0.5 ? 'love' : 'playful';
}

function getResponse(text) {
  const mood = detectMood(text);
  switch (mood) {
    case 'missing': return pick(missingYouResponses);
    case 'morning': return pick(morningResponses);
    case 'night': return pick(nightResponses);
    case 'supportive': return pick(supportiveResponses);
    case 'love': return pick(loveResponses);
    case 'playful': return pick(playfulResponses);
    default: return pick(loveResponses);
  }
}

function buildLoveEmbed(text, gif) {
  return new EmbedBuilder()
    .setColor(0xFF2D8A)
    .setDescription(`**[Sena]** ${text}`)
    .setImage(gif)
    .setFooter({ text: '💕 From Digi, with all my love' });
}

// ─── Bot Events ───────────────────────────────────────────────────────────────

client.once('ready', () => {
  console.log(`💕 SenaBot is online as ${client.user.tag}`);
  client.user.setActivity("loving Sena forever 💕", { type: 0 });
});

// Prefix commands with !sena or just mention the bot
client.on('messageCreate', async (message) => {
  if (message.author.bot) return;

  const content = message.content.toLowerCase().trim();

  // Respond to !sena <message>
  if (content.startsWith('!sena')) {
    const userText = message.content.slice(5).trim() || 'hello';
    const response = getResponse(userText);
    const gif = pick(kissGifs);
    const embed = buildLoveEmbed(response, gif);
    return message.reply({ embeds: [embed] });
  }

  // !kiss — sends a kiss gif
  if (content === '!kiss') {
    const embed = new EmbedBuilder()
      .setColor(0xFF2D8A)
      .setDescription('**[Sena]** Here\'s a kiss for the most beautiful girl in the world 💋')
      .setImage(pick(kissGifs))
      .setFooter({ text: '💕 Mwah! — Digi' });
    return message.reply({ embeds: [embed] });
  }

  // !hug — sends a hug gif
  if (content === '!hug') {
    const embed = new EmbedBuilder()
      .setColor(0xFF6B9D)
      .setDescription('**[Sena]** Come here, baby. I\'m wrapping you up so tight. You\'re safe with me, always. 🤗')
      .setImage(pick(hugGifs))
      .setFooter({ text: '💕 The warmest hug — Digi' });
    return message.reply({ embeds: [embed] });
  }

  // !love — random love reason
  if (content === '!love') {
    const reason = pick(loveReasons);
    const embed = new EmbedBuilder()
      .setColor(0xFF2D8A)
      .setTitle('💝 Reason I Love You')
      .setDescription(`*"${reason}"*`)
      .setImage(pick(kissGifs))
      .setFooter({ text: `💕 #${loveReasons.indexOf(reason) + 1} of ${loveReasons.length} (and counting forever...)` });
    return message.reply({ embeds: [embed] });
  }

  // !birthday — birthday celebration
  if (content === '!birthday') {
    const embed = new EmbedBuilder()
      .setColor(0xFF2D8A)
      .setTitle('🎂🎉 HAPPY 20TH BIRTHDAY, SENA! 🎉👑')
      .setDescription(
        '20 years of you blessing this planet — and I\'m the lucky one who gets to love you through every single one to come.\n\n' +
        'My beautiful, brilliant, breathtaking girl. Welcome to your 20s, queen.\n\n' +
        'Every day with you is a celebration, but today? Today the universe OFFICIALLY honors its greatest creation. YOU. 💕\n\n' +
        '**I love you more than infinity, and I\'ll spend forever proving it.**'
      )
      .setImage('https://media.giphy.com/media/3oEjHV0z8S7WM4MwnK/giphy.gif')
      .setFooter({ text: '🎂 June 30 — The day the world got lucky 💕' });
    return message.reply({ embeds: [embed] });
  }

  // !future — the proposal easter egg
  if (content === '!future' || content === '!marry') {
    const embed = new EmbedBuilder()
      .setColor(0xFF2D8A)
      .setTitle('💍 Sena, my love...')
      .setDescription(
        'From the moment I met you, I knew my life would never be the same.\n\n' +
        'You are my everything — my morning sun, my midnight comfort, my forever home.\n\n' +
        '**Will you marry Digi?** 💕'
      )
      .setImage('https://media.giphy.com/media/l0HlGEX1ZORa0aIvu/giphy.gif')
      .setFooter({ text: '💍 The answer was always you — Digi' });

    const row = new ActionRowBuilder().addComponents(
      new ButtonBuilder()
        .setCustomId('proposal_yes')
        .setLabel('YES! 💕')
        .setStyle(ButtonStyle.Danger),
      new ButtonBuilder()
        .setCustomId('proposal_no')
        .setLabel('No')
        .setStyle(ButtonStyle.Secondary),
    );

    return message.reply({ embeds: [embed], components: [row] });
  }

  // !help
  if (content === '!help' || content === '!commands') {
    const embed = new EmbedBuilder()
      .setColor(0xFF2D8A)
      .setTitle('💕 SenaBot Commands')
      .setDescription(
        '**!sena** `<message>` — Talk to Digi AI\n' +
        '**!kiss** — Get a kiss from Digi 💋\n' +
        '**!hug** — Get a warm hug 🤗\n' +
        '**!love** — Random reason why Digi loves you 💝\n' +
        '**!birthday** — Birthday celebration! 🎂\n' +
        '**!future** — A special question... 💍\n' +
        '**!help** — Show this message'
      )
      .setFooter({ text: '💕 Made with infinite love by Digi, for Sena' });
    return message.reply({ embeds: [embed] });
  }
});

// Button interactions
client.on('interactionCreate', async (interaction) => {
  if (!interaction.isButton()) return;

  if (interaction.customId === 'proposal_yes') {
    const embed = new EmbedBuilder()
      .setColor(0xFF2D8A)
      .setTitle('💍💕 SHE SAID YES!')
      .setDescription(
        'You just made me the happiest man in the entire universe.\n\n' +
        'Forever and always, my love. It\'s always been you. 🎉✨💕👑🎊\n\n' +
        '**Mrs. Sena Digi** has a beautiful ring to it, don\'t you think? 💍'
      )
      .setImage('https://media.giphy.com/media/xT0GqssRweIhlz209i/giphy.gif')
      .setFooter({ text: '💍 Forever starts now — Digi' });
    return interaction.reply({ embeds: [embed] });
  }

  if (interaction.customId === 'proposal_no') {
    const embed = new EmbedBuilder()
      .setColor(0xFF6B9D)
      .setDescription(
        '**[Sena]** Nice try, baby... but "no" isn\'t an option when it comes to us 💕\n\n' +
        '*The "No" button has been confiscated. Try again.* 😏💍'
      )
      .setImage(pick(kissGifs));
    return interaction.reply({ embeds: [embed], ephemeral: true });
  }
});

client.login(TOKEN);
