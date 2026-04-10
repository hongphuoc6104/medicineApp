from server.services.drug_service import DrugService


PHARMACITY_HTML = '''
<meta property="og:title" content="Viên nén Hapacol 500 mg Extra làm giảm đau các cơn đau, hạ sốt (10 vỉ x 10 viên)"/>
<meta property="og:image" content="https://prod-cdn.pharmacity.io/e-com/images/ecommerce/P01074_1.jpg"/>
<meta property="og:image" content="https://prod-cdn.pharmacity.io/e-com/images/ecommerce/P01074_3.jpg"/>
<div><span>Thương hiệu: </span><span>DHG Pharma</span></div>
<p>Số đăng ký: VD-20570-14</p>
<p>Nhà sản xuất<!-- -->:</p><div>DHG Pharma</div>
<p>Nơi sản xuất<!-- -->:</p><div>Viet Nam</div>
<p>Hoạt chất<!-- -->:</p><div>Paracetamol; Caffein</div>
<p>Dạng bào chế<!-- -->:</p><div>Viên nén</div>
<p>Quy cách<!-- -->:</p><div>10 vỉ x 10 viên</div>
'''


LONGCHAU_HTML = '''
<title>Paracetamol 500mg Thephaco (20 vỉ x 10 viên)</title>
<meta property="og:title" content="Viên nén Paracetamol 500mg Thephaco hạ sốt, giảm đau đầu (20 vỉ x 10 viên)" />
<meta property="og:image" content="https://cdn.nhathuoclongchau.com.vn/v1/static/00022271_paracetamol_large.jpg" />
<div class="font-medium"><span>Thương hiệu: </span><span>Thephaco</span></div>
<span data-test-id="sku">00022271</span>
<p>Số đăng ký</p></div><div><div><span>893100199300</span></div></div>
<p>Quy cách</p></div><div><div data-theme-element="article">Hộp 20 Vỉ x 10 Viên</div></div>
<p>Thành phần</p></div><div><div><div><div class="inline-block"><span>Paracetamol</span></div><span> (500mg)</span></div></div></div>
<p>Dạng bào chế</p></div><div><div data-theme-element="article">Viên nén</div></div>
<p>Nhà sản xuất</p></div><div><div data-theme-element="article">Thephaco</div></div>
<p>Nước sản xuất</p></div><div><div data-theme-element="article">Việt Nam</div></div>
'''


def test_parse_pharmacity_html_extracts_metadata():
    service = DrugService()
    result = service._parse_pharmacity_html(
        PHARMACITY_HTML,
        'https://www.pharmacity.vn/hapacol-extra-hop-10-vi-x-10-vien.html',
    )

    assert result['source'] == 'pharmacity'
    assert result['brandName'] == 'DHG Pharma'
    assert result['registrationNumber'] == 'VD-20570-14'
    assert result['dosageForm'] == 'Viên nén'
    assert result['manufacturer'] == 'DHG Pharma'
    assert result['country'] == 'Viet Nam'
    assert result['packaging'] == '10 vỉ x 10 viên'
    assert result['activeIngredients'] == [
        {'name': 'Paracetamol', 'strength': '', 'source': 'pharmacity'},
        {'name': 'Caffein', 'strength': '', 'source': 'pharmacity'},
    ]
    assert len(result['images']) == 2


def test_parse_longchau_html_extracts_metadata():
    service = DrugService()
    result = service._parse_longchau_html(
        LONGCHAU_HTML,
        'https://nhathuoclongchau.com.vn/thuoc/paracetamol-500mg-thephaco-20x10-22630.html',
    )

    assert result['source'] == 'longchau'
    assert result['brandName'] == 'Thephaco'
    assert result['registrationNumber'] == '893100199300'
    assert result['dosageForm'] == 'Viên nén'
    assert result['manufacturer'] == 'Thephaco'
    assert result['country'] == 'Việt Nam'
    assert result['packaging'] == 'Hộp 20 Vỉ x 10 Viên'
    assert result['activeIngredients'] == [
        {'name': 'Paracetamol', 'strength': '', 'source': 'longchau'},
    ]
    assert len(result['images']) == 1
    assert any('sku: 00022271' in note for note in result['notes'])


def test_score_product_url_prefers_closer_slug_match():
    service = DrugService()
    better = service._score_product_url(
        'Hapacol 500mg Extra',
        'https://www.pharmacity.vn/hapacol-extra-hop-10-vi-x-10-vien.html',
    )
    worse = service._score_product_url(
        'Hapacol 500mg Extra',
        'https://www.pharmacity.vn/panadol-500mg-vien-sui-2721.html',
    )

    assert better > worse
