import importlib.util, json, subprocess, tempfile, unittest
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('renderer',ROOT/'scripts/render_orbiuno_4.py')
renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)
spec2=importlib.util.spec_from_file_location('alignment',ROOT/'scripts/verify_alignment.py')
alignment=importlib.util.module_from_spec(spec2);spec2.loader.exec_module(alignment)

class TestORBIUNO(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name)
        (self.base/'images').mkdir();(self.base/'audio').mkdir()
        Image.new('RGB',(400,600),'blue').save(self.base/'images/test.jpg')
        for i in range(6):
            subprocess.run(['ffmpeg','-loglevel','error','-y','-f','lavfi','-i','sine=frequency=440:duration=1',
                '-c:a','pcm_s16le',str(self.base/f'audio/{i}.wav')],check=True)
        self.data={
            'brand':'ORBIUNO','editionDate':'2026-11-10','slot':'20:00',
            'voice':{'name':'Camila Vega','id':renderer.VOICE_ID,'speed':1.25,'recordedAtSpeed':1.0},
            'intro':{'narration':'Orbiuno. Noticias de Colombia y el mundo.','audioFile':'audio/0.wav'},
            'outro':{'narration':'Síguenos. Puedes escuchar noticias en colombia-al-dia punto pages punto dev.','audioFile':'audio/5.wav'},
            'news':[{'id':f'news{i}','date':'2026-11-10','category':'Colombia','verification':'editorial_verified','title':f'Noticia distinta número {i}',
              'narration':'Texto editorial verificado.', 'audioFile':f'audio/{i}.wav',
              'source':{'name':'Medio','url':f'https://example.org/noticias/{i}'},
              'image':{'file':'images/test.jpg','sourceUrl':'https://example.org/imagen','credit':'Autor','license':'CC BY 4.0','rightsVerified':True}} for i in range(1,5)],
            'approval':{}
        }
    def tearDown(self):self.tmp.cleanup()
    def test_valid_preview(self):self.assertTrue(renderer.validate(self.data,self.base))
    def test_refuse_unknown_voice(self):
        self.data['voice']['name']='Otra';self.assertRaises(ValueError,renderer.validate,self.data,self.base)
    def test_refuse_not_four(self):
        self.data['news'].pop();self.assertRaises(ValueError,renderer.validate,self.data,self.base)
    def test_refuse_unverified(self):
        self.data['news'][0]['verification']='source_only';self.assertRaises(ValueError,renderer.validate,self.data,self.base)
    def test_refuse_unlicensed_image(self):
        self.data['news'][0]['image']['rightsVerified']=False;self.assertRaises(ValueError,renderer.validate,self.data,self.base)
    def test_refuse_wrong_speed(self):
        self.data['voice']['speed']=1.0;self.assertRaises(ValueError,renderer.validate,self.data,self.base)
    def test_refuse_release_without_approval(self):self.assertRaises(ValueError,renderer.validate,self.data,self.base,True)
    def test_approved_after_gates(self):
        self.data['music']={'file':'audio/0.wav','sourceUrl':'https://example.org/music/track','credit':'Test Music','license':'Test only','rightsVerified':True}
        self.data['approval']={g:True for g in renderer.RELEASE_GATES}
        self.assertTrue(renderer.validate(self.data,self.base,True))
    def test_path_traversal(self):
        self.data['news'][0]['image']['file']='../../etc/passwd'
        self.assertRaises(ValueError,renderer.validate,self.data,self.base)
    def test_web_alignment_mismatch(self):
        m=self.base/'manifest.json';n=self.base/'noticias.json'
        m.write_text(json.dumps(self.data),encoding='utf-8');n.write_text(json.dumps({'news':[]}),encoding='utf-8')
        self.assertRaises(RuntimeError,alignment.check,m,n,'')

if __name__=='__main__':unittest.main()
