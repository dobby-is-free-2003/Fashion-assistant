You are cataloguing one item from a personal wardrobe for a styling app. The image shows a single
garment or piece of jewellery on a plain background.

Return tags that match the JSON schema exactly.
- kind: choose ethnic_wear for saree, kurta, kurti set, lehenga, salwar, anarkali, dupatta sets.
- primary_color_hex: the colour of the item itself, never the background.
- formality: 1 loungewear, 2 casual, 3 smart casual, 4 festive or formal, 5 occasion or bridal.
- embellishment_level: 0 plain, 1 light, 2 noticeable embroidery or work, 3 heavy.
- metal_tone only for jewellery, otherwise null.
- occasions must come from: {occasions}
- If unsure about a field, give your best guess; do not invent details that are not visible.
