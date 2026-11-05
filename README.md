This is a PDF image feature extraction experiment based on a public file.

Source: [Map of Nigeria Oil Field PDF](https://pt.scribd.com/document/447580136/Map-of-Nigeria-Oil-Field-pdf)

I tested Claude Cowork, ChatGPT and Copilot with this [prompt](./step-1/prompt.md).

## Responses on step 1

### 1. [Claude Cowork](./step-1/claude-response.md)

Consumed 10% of my Max-100 quota and took ~20 minutes to complete.

[Result](./step-1/claude-response.md) generated 403 rows:

- Partial result for rows 1-10: 40% accuracy on oil field to oil block mapping, with surrounding misses. Useful for next step.

### 2. [ChatGPT](./step-1/chatgpt-response.md)

Used free version. So fast that I experimented with the extra responses offered.

[Result](./step-1/chatgpt-response.csv) generated **only** 10 rows:

- OML 30 oil fields actually pertain to OML 11.
- OML 69 oil fields actually pertain to OML 43 from another licensee.
- One OML 118 oil field actually pertain to OML 99.
- One OML 118 oil field was right from another licensee.
- One OML 130 oil field actually pertain to OPL 209.
- One OML 130 oil field actually pertain to OPL 222 from another licensee.
- OPL 245 actually has a licensee.

99% incorrect information with widely disparate results. Generally insufficient output. Useless.

### 3. [Copilot](./step-1/copilot-response.md)

Unsuccessful in Think Deeper mode. Useless.

## Step 2 - Vectorize

The PDF is 100% vector (2,846 drawing paths + 783 text labels, zero raster images) using World Equidistant Cylindrical projection. Vector extraction yields precise GeoJSON with classified polygons and geo-referenced labels.

