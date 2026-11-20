"""Project templates per genre (no LLM — static data).

Each template: genre, title_suggestion, premise, main_plot, subplots,
tone_and_visual_style, world_settings, ending_direction,
episode_structure, characters (4-5: name/role/background), locations
(3-4: name/type/description).
"""
from copy import deepcopy

TEMPLATES: dict[str, dict] = {
    "romance": {
        "genre": "romance",
        "title_suggestion": "Cinta di Balik Hujan",
        "premise": "Seorang koki muda yang kehilangan indera perasa bertemu fotografer yang menyimpan rahasia masa lalu; keduanya saling menyembuhkan lewat masakan dan foto yang tak pernah dicetak.",
        "main_plot": "Nadia, koki berbakat yang kehilangan kemampuan mengecap rasa setelah kecelakaan, hampir menutup restorannya. Arka, fotografer yang kembali ke kota setelah 10 tahun menghilang, menjadi pelanggan tetap yang selalu memesan menu yang sama. Lewat catatan rasa yang ditulis Arka untuk setiap hidangan, Nadia perlahan menemukan kembali rasanya — dan alasan Arka pergi dulu.",
        "subplots": [
            "Persaingan Nadia dengan restoran baru milik mantan mentornya",
            "Arka menyembunyikan bahwa ia memotret kecelakaan yang merenggut kemampuan Nadia",
            "Persahabatan Nadia dengan pemilik pasar yang menjadi mak comblang",
        ],
        "tone_and_visual_style": "Hangat dan intim; warna keemasan sore hari, close-up masakan dan tangan, hujan sebagai motif visual yang berulang.",
        "world_settings": "Kota kecil pesisir dengan pasar tradisional, restoran keluarga di tepi jalan, dan studio foto tua di lantai dua.",
        "ending_direction": "Nadia memasak menu terakhir untuk Arka dengan rasa yang kembali penuh; Arka mencetak foto yang selama ini ia simpan dan memberikannya sebagai pengakuan.",
        "episode_structure": "Episode 1-3: pertemuan dan restoran di ambang tutup; 4-8: catatan rasa dan kedekatan yang tumbuh; 9-14: rahasia masa lalu terungkap; 15-18: perpisahan dan pilihan; 19-20: menu terakhir dan pengakuan.",
        "characters": [
            {"name": "Nadia", "role": "protagonist", "background": "Koki 27 tahun, pemilik restoran keluarga; kehilangan indera perasa setelah kecelakaan dua tahun lalu."},
            {"name": "Arka", "role": "protagonist", "background": "Fotografer 30 tahun yang kembali setelah 10 tahun; menyimpan foto kecelakaan Nadia yang tak pernah ia cetak."},
            {"name": "Bu Ratna", "role": "supporting", "background": "Ibu Nadia, penjaga resep keluarga; diam-diam berharap Nadia menutup restoran dan hidup tenang."},
            {"name": "Dimas", "role": "antagonist", "background": "Mantan mentor Nadia yang kini membuka restoran modern seberang jalan dan ingin membeli lahan restoran Nadia."},
            {"name": "Sinta", "role": "supporting", "background": "Pemilik kios pasar, sahabat Nadia sejak kecil, penghubung gosip dan kebenaran di kota."},
        ],
        "locations": [
            {"name": "Restoran Senja", "type": "interior", "description": "Restoran keluarga Nadia yang hangat dan agak sepi; dapur terbuka, meja kayu tua, lampu gantung kuning."},
            {"name": "Pasar Pesisir", "type": "exterior", "description": "Pasar tradisional yang ramai di pagi hari; tempat Nadia memilih bahan dan Sinta berjualan."},
            {"name": "Studio Foto Arka", "type": "interior", "description": "Studio tua berdebu di lantai dua; kamar gelap tempat Arka menyimpan foto yang tak pernah dicetak."},
            {"name": "Dermaga Hujan", "type": "exterior", "description": "Dermaga kayu tempat Nadia dan Arka berbicara saat hujan; lokasi pengakuan di episode akhir."},
        ],
    },
    "thriller": {
        "genre": "thriller",
        "title_suggestion": "Sinyal Terakhir",
        "premise": "Seorang operator call center darurat menerima telepon dari nomornya sendiri — suara di seberang tahu semua yang akan terjadi 10 menit ke depan.",
        "main_plot": "Rani, operator 112, menerima panggilan dari nomor pribadinya sendiri. Penelepon — suaranya sendiri — memperingatkan kecelakaan yang terjadi tepat 10 menit kemudian. Setiap panggilan menyelamatkan seseorang, tapi setiap penyelamatan mengubah sesuatu yang lain. Rani sadar penelepon itu adalah dirinya dari masa depan yang mencoba mencegah satu kematian: kematian adiknya.",
        "subplots": [
            "Rekan kerja Rani curiga ia membocorkan data panggilan darurat",
            "Polisi menyelidiki pola kecelakaan yang 'kebetulan' selalu dicegah",
            "Rani menemukan rekaman panggilan lama dari malam adiknya meninggal",
        ],
        "tone_and_visual_style": "Tegang dan dingin; dominan biru dan hijau monitor, jam dinding sebagai motif, potongan cepat antara ruang kontrol dan lokasi kejadian.",
        "world_settings": "Pusat kendali darurat kota besar yang beroperasi 24 jam; apartemen kecil Rani yang penuh catatan dan rekaman.",
        "ending_direction": "Rani memilih tidak menjawab panggilan terakhir — menerima bahwa beberapa hal tidak bisa diubah, dan adiknya tetap hidup karena pilihan lain yang ia buat.",
        "episode_structure": "Episode 1-3: panggilan pertama dan kecelakaan yang dicegah; 4-8: pola 10 menit dan harga setiap penyelamatan; 9-14: penyelidikan polisi dan rekaman lama; 15-18: identitas penelepon terungkap; 19-20: panggilan terakhir dan pilihan Rani.",
        "characters": [
            {"name": "Rani", "role": "protagonist", "background": "Operator darurat 29 tahun; kehilangan adiknya dalam kecelakaan yang tak pernah terungkap penyebabnya."},
            {"name": "Suara", "role": "mysterious", "background": "Penelepon misterius bersuara sama dengan Rani; tahu masa depan 10 menit dan hanya menelepon saat nyawa dipertaruhkan."},
            {"name": "Bimo", "role": "supporting", "background": "Rekan shift malam Rani; satu-satunya yang percaya ada yang aneh dengan panggilan-panggilan itu."},
            {"name": "Komisaris Hadi", "role": "antagonist", "background": "Penyidik yang yakin Rani terlibat dalam rangkaian kecelakaan yang selalu 'kebetulan' dicegah."},
            {"name": "Laras", "role": "supporting", "background": "Adik Rani yang meninggal; hadir lewat rekaman, foto, dan ingatan yang perlahan berubah."},
        ],
        "locations": [
            {"name": "Ruang Kendali 112", "type": "interior", "description": "Ruangan dingin penuh monitor dan headset; jam digital besar di dinding, lampu merah saat panggilan masuk."},
            {"name": "Apartemen Rani", "type": "interior", "description": "Apartemen sempit dengan dinding penuh catatan waktu, peta kota, dan kaset rekaman lama."},
            {"name": "Jembatan Kota", "type": "exterior", "description": "Jembatan tempat kecelakaan pertama dicegah; lokasi klimaks saat Rani memilih tidak menjawab."},
        ],
    },
    "revenge": {
        "genre": "revenge",
        "title_suggestion": "Istri yang Diremehkan",
        "premise": "Setelah 10 tahun direndahkan keluarga suaminya, seorang istri yang dianggap tak berguna diam-diam membangun kerajaan bisnis — lalu kembali untuk menagih semua penghinaan, satu per satu.",
        "main_plot": "Nadia menikah muda ke keluarga kaya dan diperlakukan seperti pembantu selama 10 tahun. Saat suaminya berselingkuh dan ibu mertuanya mengusirnya tanpa apa-apa, Nadia menghilang. Tiga tahun kemudian ia kembali sebagai pemilik perusahaan yang membeli utang keluarga itu — dengan nama baru, wajah yang sama, dan daftar panjang orang yang harus membayar.",
        "subplots": [
            "Anak Nadia yang dibesarkan keluarga mertua mulai mengenalinya",
            "Selingkuhan suami ternyata bekerja untuk perusahaan Nadia",
            "Pengacara keluarga mertua menemukan celah hukum dalam akuisisi Nadia",
        ],
        "tone_and_visual_style": "Elegan dan tajam; kontras kemewahan dingin keluarga mertua dengan kehangatan hidup baru Nadia; tatapan kamera yang lama dan sunyi.",
        "world_settings": "Kota besar dengan rumah mewah keluarga konglomerat, kantor pusat perusahaan Nadia, dan rumah sederhana tempat Nadia memulai lagi.",
        "ending_direction": "Nadia tidak menghancurkan keluarga itu — ia memberi mereka pilihan yang sama seperti yang dulu diberikan padanya, dan membiarkan mereka merasakan menjadi bukan siapa-siapa.",
        "episode_structure": "Episode 1-3: penghinaan dan pengusiran; 4-8: Nadia membangun bisnis dari nol; 9-14: kembali dengan identitas baru, balas dendam bertahap; 15-18: keluarga mertua sadar siapa dia; 19-20: pilihan terakhir dan penagihan.",
        "characters": [
            {"name": "Nadia", "role": "protagonist", "background": "Istri 32 tahun yang direndahkan 10 tahun; kini CEO perusahaan investasi yang membeli utang keluarga mantannya."},
            {"name": "Raka", "role": "antagonist", "background": "Mantan suami Nadia; pewaris manja yang menghancurkan perusahaan keluarga demi selingkuhannya."},
            {"name": "Ratna", "role": "antagonist", "background": "Ibu mertua Nadia; perempuan berwibawa yang mengusir Nadia dan kini memohon belas kasihan."},
            {"name": "Kevin", "role": "supporting", "background": "Anak Nadia dan Raka, 9 tahun; dibesarkan keluarga mertua dan mulai bertanya tentang ibunya."},
            {"name": "Arman", "role": "supporting", "background": "Pengacara tua yang membantu Nadia sejak awal; satu-satunya yang tahu seluruh rencananya."},
        ],
        "locations": [
            {"name": "Rumah Keluarga Raka", "type": "interior", "description": "Mansion mewah yang dingin; ruang makan besar tempat Nadia selalu disuruh makan di dapur."},
            {"name": "Kantor Nadia", "type": "interior", "description": "Kantor modern di lantai 40; kaca, baja, dan pemandangan kota — simbol kekuasaan baru Nadia."},
            {"name": "Rumah Kontrakan Nadia", "type": "interior", "description": "Rumah kecil tempat Nadia memulai lagi; hangat, sederhana, penuh rencana di dinding."},
            {"name": "Gala Amal Tahunan", "type": "interior", "description": "Ballroom mewah tempat keluarga mertua pamer kekuasaan — dan tempat Nadia pertama kali menampakkan diri."},
        ],
    },
    "family": {
        "genre": "family",
        "title_suggestion": "Warisan Ayah",
        "premise": "Empat bersaudara yang sudah bertahun-tahun tak bicara harus tinggal serumah selama 40 hari untuk mendapatkan warisan ayah mereka — dan menemukan surat-surat yang mengubah semua yang mereka kira tahu.",
        "main_plot": "Ayah mereka meninggal meninggalkan wasiat aneh: warisan hanya cair jika keempat anaknya tinggal bersama di rumah keluarga selama 40 hari tanpa pergi. Di balik aturan itu, sang ayah meninggalkan surat untuk masing-masing anak yang mengungkap rahasia keluarga: siapa sebenarnya ibu mereka, dari mana harta itu berasal, dan mengapa mereka dijauhkan satu sama lain.",
        "subplots": [
            "Si sulung menyembunyikan bahwa perusahaannya bangkrut dan butuh warisan",
            "Si bungsu membawa pacar yang ternyata anak dari musuh lama ayah",
            "Surat-surat ayah hilang satu per satu — ada yang mencurinya",
        ],
        "tone_and_visual_style": "Hangat, lucu, dan getir; rumah tua sebagai karakter; makan malam bersama sebagai adegan kunci yang berulang.",
        "world_settings": "Rumah keluarga besar di pinggir kota dengan kebun mangga, warung tetangga, dan ruang tamu yang tak pernah berubah sejak 1990-an.",
        "ending_direction": "Keempatnya memilih membagi warisan dan merenovasi rumah bersama — bukan karena wasiat, tapi karena akhirnya mereka saling mengenal lagi.",
        "episode_structure": "Episode 1-3: pemakaman dan wasiat aneh; 4-8: tinggal serumah, konflik lama meledak; 9-14: surat-surat ayah dan rahasia terungkap; 15-18: pencuri surat dan kebenaran terakhir; 19-20: keputusan warisan dan rumah baru.",
        "characters": [
            {"name": "Bagas", "role": "protagonist", "background": "Anak sulung 38 tahun; pengusaha yang perusahaannya bangkrut diam-diam; paling ngotot soal warisan."},
            {"name": "Kirana", "role": "protagonist", "background": "Anak kedua 35 tahun; dokter yang pindah ke luar kota untuk menjauh dari keluarga."},
            {"name": "Dimas", "role": "supporting", "background": "Anak ketiga 31 tahun; musisi gagal yang paling dekat dengan ayah dan paling tahu rahasianya."},
            {"name": "Laras", "role": "protagonist", "background": "Si bungsu 26 tahun; membawa pacar baru yang menyimpan kaitan dengan masa lalu ayah."},
            {"name": "Mbah Sari", "role": "supporting", "background": "Tetangga tua yang tahu semua rahasia keluarga tapi hanya bicara lewat peribahasa."},
        ],
        "locations": [
            {"name": "Rumah Keluarga", "type": "interior", "description": "Rumah tua dua lantai dengan kebun mangga; ruang tamu, dapur, dan kamar ayah yang dikunci."},
            {"name": "Warung Mbah Sari", "type": "exterior", "description": "Warung kecil di ujung gang; tempat gosip, nasihat, dan kebenaran setengah-setengah."},
            {"name": "Kantor Notaris", "type": "interior", "description": "Kantor sempit tempat wasiat dibacakan; awal dari 40 hari yang mengubah segalanya."},
        ],
    },
    "ceo_billionaire": {
        "genre": "ceo_billionaire",
        "title_suggestion": "CEO Penyamar",
        "premise": "Seorang CEO miliarder menyamar menjadi karyawan magang di perusahaannya sendiri untuk menemukan siapa yang mencuri dari dalam — dan jatuh cinta pada perempuan yang membencinya tanpa tahu siapa dia.",
        "main_plot": "Adrian, CEO 32 tahun, menemukan kebocoran dana besar di perusahaannya. Alih-alih memanggil auditor, ia menyamar sebagai Adi, karyawan magang baru di divisi keuangan. Di sana ia bertemu Maya, auditor internal yang tajam dan membenci CEO yang tak pernah ia temui. Sambil memburu pencuri dari dalam, Adrian harus menjaga penyamarannya — dan menyembunyikan bahwa ia jatuh cinta pada perempuan yang sedang menyelidiki dirinya.",
        "subplots": [
            "Direktur keuangan ternyata dalang pencurian dan dekat dengan keluarga Adrian",
            "Maya hampir menemukan identitas asli Adi dari sidik jari di dokumen",
            "Ibu Adrian menjodohkannya dengan putri rekan bisnis tanpa tahu ia menyamar",
        ],
        "tone_and_visual_style": "Glamor dan cepat; kontras kantor kaca pencakar langit dengan sudut-sudut kota; musik upbeat, potongan tajam.",
        "world_settings": "Kantor pusat konglomerat di distrik bisnis, apartemen mewah Adrian, dan kos sederhana tempat 'Adi' tinggal selama penyamaran.",
        "ending_direction": "Adrian membuka identitasnya di depan seluruh kantor saat menangkap pencuri — dan Maya memilih memaafkan, dengan satu syarat: Adrian magang sungguhan di divisinya selama sebulan.",
        "episode_structure": "Episode 1-3: kebocoran dana dan penyamaran dimulai; 4-8: Adi dan Maya, penyelidikan ganda; 9-14: pencuri makin dekat, penyamaran hampir terbongkar; 15-18: identitas terancam dan pengkhianatan direktur; 19-20: pengungkapan dan pilihan Maya.",
        "characters": [
            {"name": "Adrian / Adi", "role": "protagonist", "background": "CEO miliarder 32 tahun yang menyamar jadi karyawan magang untuk memburu pencuri di perusahaannya."},
            {"name": "Maya", "role": "protagonist", "background": "Auditor internal 28 tahun; tajam, jujur, dan membenci CEO yang menurutnya serakah tanpa pernah bertemu."},
            {"name": "Hendro", "role": "antagonist", "background": "Direktur keuangan dan teman lama keluarga Adrian; dalang kebocoran dana selama bertahun-tahun."},
            {"name": "Sinta", "role": "supporting", "background": "Sekretaris Adrian yang menjaga rahasia penyamaran dan menjadi kaki tangan setia."},
            {"name": "Bimo", "role": "supporting", "background": "Karyawan magang lain yang menjadi sahabat 'Adi'; tidak tahu siapa sebenarnya teman sekamarnya."},
        ],
        "locations": [
            {"name": "Kantor Pusat Adrian Corp", "type": "interior", "description": "Menara kaca 50 lantai; ruang CEO di puncak dan divisi keuangan yang ramai di lantai 12."},
            {"name": "Kos Adi", "type": "interior", "description": "Kamar kos sempit tempat Adrian tinggal selama menyamar; kontras total dengan penthouse-nya."},
            {"name": "Penthouse Adrian", "type": "interior", "description": "Apartemen mewah yang hampir tak pernah ditinggali selama penyamaran; simbol hidup ganda Adrian."},
            {"name": "Rooftop Gala", "type": "exterior", "description": "Rooftop tempat gala perusahaan; lokasi pengungkapan identitas Adrian di episode akhir."},
        ],
    },
    "fantasy": {
        "genre": "fantasy",
        "title_suggestion": "Penjaga Gerbang Senja",
        "premise": "Di pasar malam yang hanya muncul saat gerhana, seorang penjual jamu mewarisi gerbang antara dunia manusia dan dunia makhluk halus — dan harus memilih sisi mana yang ia lindungi saat perang lama bangkit lagi.",
        "main_plot": "Sari, penjual jamu 24 tahun di pasar malam, menemukan bahwa lapaknya berdiri di atas gerbang kuno antara dua dunia. Saat gerhana terakhir membuka gerbang itu, makhluk-makhluk lama kembali menagih janji yang dibuat leluhurnya. Sari harus belajar menjadi Penjaga — dengan bantuan arwah neneknya dan seorang makhluk yang seharusnya menjadi musuhnya.",
        "subplots": [
            "Makhluk yang membantu Sari ternyata anak dari raja yang memulai perang dulu",
            "Pasar malam mulai menghilang dari ingatan manusia satu per satu",
            "Adik Sari tanpa sengaja memakan buah terlarang dan perlahan berubah",
        ],
        "tone_and_visual_style": "Magis dan gelap-keemasan; pasar malam dengan lentera, kabut, dan warna yang tak ada di dunia nyata; makhluk dirancang dari mitologi lokal.",
        "world_settings": "Pasar malam gaib yang muncul saat gerhana; desa Sari di dunia manusia; dan hutan terbalik di balik gerbang tempat waktu berjalan mundur.",
        "ending_direction": "Sari tidak menutup gerbang — ia menulis perjanjian baru antara dua dunia, dan pasar malam kini muncul setiap bulan purnama untuk siapa saja yang berani datang.",
        "episode_structure": "Episode 1-3: gerhana dan gerbang terbuka; 4-8: Sari belajar menjadi Penjaga; 9-14: perang lama dan janji leluhur; 15-18: adik Sari berubah, pasar menghilang; 19-20: perjanjian baru dan pasar purnama.",
        "characters": [
            {"name": "Sari", "role": "protagonist", "background": "Penjual jamu 24 tahun; keturunan Penjaga gerbang yang tak pernah tahu warisannya sampai gerhana terakhir."},
            {"name": "Rangga", "role": "protagonist", "background": "Makhluk penjaga hutan terbalik; anak raja yang memulai perang lama; membantu Sari dengan harga yang belum ia sebutkan."},
            {"name": "Nenek Wulan", "role": "supporting", "background": "Arwah nenek Sari, Penjaga sebelumnya; membimbing lewat mimpi dan resep jamu yang ternyata mantra."},
            {"name": "Raja Kelam", "role": "antagonist", "background": "Raja dunia balik gerbang yang menagih janji leluhur Sari: gerbang dibuka selamanya, atau perang dimulai lagi."},
            {"name": "Bima", "role": "supporting", "background": "Adik Sari, 16 tahun; memakan buah terlarang dan perlahan berubah menjadi makhluk gerbang."},
        ],
        "locations": [
            {"name": "Pasar Malam Gerhana", "type": "exterior", "description": "Pasar gaib yang hanya muncul saat gerhana; lentera melayang, lapak yang menjual kenangan dan mimpi."},
            {"name": "Lapak Jamu Sari", "type": "exterior", "description": "Lapak kecil di ujung pasar; di bawahnya tersembunyi gerbang kuno antara dua dunia."},
            {"name": "Hutan Terbalik", "type": "exterior", "description": "Hutan di balik gerbang tempat pohon tumbuh ke bawah dan waktu berjalan mundur."},
            {"name": "Desa Sari", "type": "exterior", "description": "Desa tenang di dunia manusia; pasar biasa di siang hari, gerbang di malam gerhana."},
        ],
    },
}


def list_templates() -> list[dict]:
    """Summary list: genre + title suggestion + short premise."""
    result = []
    for template in TEMPLATES.values():
        premise = template["premise"]
        short = premise if len(premise) <= 200 else premise[:197] + "..."
        result.append({
            "genre": template["genre"],
            "title_suggestion": template["title_suggestion"],
            "premise": short,
        })
    return result


def get_template(genre: str) -> dict | None:
    template = TEMPLATES.get(genre)
    if template is None:
        return None
    return deepcopy(template)
