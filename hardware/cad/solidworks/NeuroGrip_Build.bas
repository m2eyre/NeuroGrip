Attribute VB_Name = "NeuroGrip_Build"
'==============================================================================
' NeuroGrip  -  two-finger gear gripper (1x SG90) + adjustable wrist mount
' SolidWorks VBA macro: builds 5 parts and a movable assembly.
' v2: screwless. Base slides onto a dovetail rail (locked with a 1.75 mm filament pin),
'     idler finger snaps onto a printed split pin. Only the SG90 tab/horn screws remain.
'
' HOW TO RUN
'   1. SolidWorks > Tools > Macro > New...  save as NeuroGrip.swp in an EMPTY folder
'   2. In the VBA editor: File > Import File... > NeuroGrip_Build.bas
'      (or paste this whole file into Module1). Delete the empty "Sub main" if one exists.
'   3. Run "main" (F5). Parts + assembly are saved to <macro folder>\NeuroGrip_CAD\
'   4. In the assembly, drag either finger: both fingers move equally (gear mate),
'      limited to 0..35 degrees of opening.
'
' Coordinates: every gripper part is sketched on its Top plane (height = +Y).
' Sketch x = model X, sketch y = "forward" (direction the fingers point).
' All dimensions below are millimetres. Measure YOUR servo and edit the SG90 block.
'==============================================================================
Option Explicit

Const PI As Double = 3.14159265358979

' ---- gears ----
Const G_M As Double = 1.5          ' module
Const G_Z As Long = 14             ' teeth
Const CD_EXTRA As Double = 0.2     ' extra centre distance for FDM
Const BACKLASH As Double = 0.2     ' arc removed from each tooth at pitch circle
Const GEAR_T As Double = 6#        ' gear + finger thickness

' ---- SG90 (datasheet values, check with calipers) ----
Const SV_L As Double = 22.5
Const SV_W As Double = 12.2
Const SV_H As Double = 22.7
Const SV_SHAFT_OFF As Double = 5.35    ' shaft centre to body centre
Const SV_TAB_SPAN As Double = 32.2
Const SV_TAB_T As Double = 2.5
Const SV_TAB_Z As Double = 15.9        ' body bottom to underside of tabs
Const SV_TAB_HOLE_PITCH As Double = 27.8
Const SV_TAB_HOLE_D As Double = 2#
Const SV_BUMP_D As Double = 11.8
Const SV_BUMP_H As Double = 4#
Const SV_SPLINE_D As Double = 4.8
Const SV_SPLINE_TOP As Double = 30.5
Const HORN_SEAT As Double = 29.5       ' body bottom to underside of horn arm (= gear bottom)
Const FIT As Double = 0.25             ' clearance per side

' ---- single-arm horn pocket in the driver gear ----
Const HORN_HUB_D As Double = 7.6
Const HORN_LEN As Double = 17.5        ' hub centre to arm tip centre
Const HORN_W0 As Double = 6.4          ' arm width at hub
Const HORN_W1 As Double = 4.6          ' arm width at tip
Const HORN_DEPTH As Double = 2#
Const HORN_FIT As Double = 0.1         ' clearance per side on the horn arm (tight)
Const RIB_D As Double = 1.2            ' crush ribs inside the horn pocket
Const RIB_IN As Double = 0.35          ' how far each rib sticks into the pocket (squeeze = RIB_IN - HORN_FIT)

' ---- base ----
Const FLOOR_T As Double = 5#          ' floor under the servo (dovetail groove runs below it)
Const BASE_X0 As Double = -9.5
Const BASE_D0 As Double = -24#
Const BASE_D1 As Double = 13#
Const PILLAR_D As Double = 10#
Const PILLAR_BOSS_D As Double = 6#
Const PILLAR_GAP As Double = 0.3
Const PIN_D As Double = 5#             ' printed snap pin shank (idler pivot)
Const PIN_HOLE_D As Double = 5.4       ' hole in the idler gear
Const PIN_BARB_D As Double = 5.9       ' barb that snaps over the idler gear
Const PIN_SLOT_W As Double = 1.6       ' split that lets the pin squeeze in
Const RAIL_X As Double = 14#           ' dovetail axis in base frame
Const WIRE_W As Double = 8.5
Const WIRE_ABOVE_FLOOR As Double = 9.5 ' height of the cable windows above the servo bottom

' ---- dovetail slide (tongue on wrist mount, groove under base) ----
Const DT_NECK As Double = 8#
Const DT_TOP As Double = 12#
Const DT_H As Double = 4.5
Const DT_FIT As Double = 0.25          ' clearance per side in the groove
Const LOCK_PIN_D As Double = 2.2       ' cross hole for a 1.75 mm filament lock pin
Const LOCK_PITCH As Double = 6#        ' rail lock holes every 6 mm
Const LOCK_N As Long = 4               ' holes at 0, +-6 ... +-24

' ---- fingers ----
Const JAW_D0 As Double = 26#
Const JAW_D1 As Double = 48#
Const JAW_W As Double = 7#
Const JAW_GAP As Double = 2#           ' gap between jaw faces when closed
Const NOTCH_DEPTH As Double = 1.2

' ---- wrist mount ----
Const WR_RI As Double = 38#            ' inner radius of the wrist saddle
Const WR_T As Double = 3.5
Const WR_ANG As Double = 65#           ' half angle of the saddle
Const WR_LEN As Double = 60#
Const RAIL_W As Double = 40#
Const RAIL_PLAT As Double = 8#        ' top of the flat platform the base sits on
Const STRAP_X0 As Double = 29#
Const STRAP_X1 As Double = 33#
Const STRAP_LEN As Double = 26#        ' for 25 mm velcro

' ---- assembly ----
Const OPEN_LIMIT_DEG As Double = 35#

Dim swApp As Object
Dim OUT_DIR As String
Dim LogText As String
Dim PlaneList As Collection

' derived
Dim CD As Double, DECK As Double, GEAR_Z As Double, RAIL_TOP As Double, BASE_X1 As Double
Dim JAW_IN As Double, JAW_OUT As Double

' gear point buffer
Dim gx() As Double, gy() As Double, gn As Long
Dim g_rb As Double, g_psi As Double, g_ap As Double

'==============================================================================
Sub main()
    Set swApp = Application.SldWorks
    LogText = ""
    CD = G_M * G_Z + CD_EXTRA
    DECK = FLOOR_T + SV_TAB_Z
    GEAR_Z = FLOOR_T + HORN_SEAT
    RAIL_TOP = RAIL_PLAT
    BASE_X1 = CD + 5.5
    JAW_IN = CD / 2 - JAW_GAP / 2
    JAW_OUT = JAW_IN - JAW_W

    OUT_DIR = swApp.GetCurrentMacroPathFolder
    If Right(OUT_DIR, 1) <> "\" Then OUT_DIR = OUT_DIR & "\"
    OUT_DIR = OUT_DIR & "NeuroGrip_CAD\"
    If Dir(OUT_DIR, vbDirectory) = "" Then MkDir OUT_DIR

    Dim pBase As String, pServo As String, pDrv As String, pIdl As String, pWr As String
    pBase = BuildBase()
    pServo = BuildServo()
    pDrv = BuildFinger(True)
    pIdl = BuildFinger(False)
    pWr = BuildWristMount()
    BuildAssembly pBase, pServo, pDrv, pIdl, pWr

    MsgBox "NeuroGrip built in:" & vbCrLf & OUT_DIR & vbCrLf & vbCrLf & _
           IIf(LogText = "", "All features and mates OK.", "Notes:" & vbCrLf & LogText), vbInformation, "NeuroGrip"
End Sub

'============================== helpers =======================================
Function mm(ByVal v As Double) As Double
    mm = v / 1000#
End Function

Sub LogMsg(s As String)
    LogText = LogText & "- " & s & vbCrLf
    Debug.Print s
End Sub

Function NewDoc(isAsm As Boolean) As Object
    Dim t As String
    t = swApp.GetUserPreferenceStringValue(IIf(isAsm, 9, 8))
    If t = "" Then t = swApp.GetDocumentTemplate(IIf(isAsm, 2, 1), "", 0, 0, 0)
    Set NewDoc = swApp.NewDocument(t, 0, 0, 0)
    If NewDoc Is Nothing Then
        MsgBox "Could not create a new document. Set a default Part/Assembly template in " & _
               "Tools > Options > Default Templates.", vbCritical
        End
    End If
End Function

' rename the three default planes to PFront / PTop / PRight (language independent)
Sub RenameDefaultPlanes(m As Object)
    Dim f As Object, i As Long
    Set f = m.FirstFeature
    Do While Not f Is Nothing
        If f.GetTypeName2 = "RefPlane" Then
            i = i + 1
            If i = 1 Then f.Name = "PFront"
            If i = 2 Then f.Name = "PTop"
            If i = 3 Then f.Name = "PRight": Exit Do
        End If
        Set f = f.GetNextFeature
    Loop
End Sub

Function SafeName(prefix As String, v As Double) As String
    Dim s As String
    s = Format(v, "0.00")
    s = Replace(s, ".", "p"): s = Replace(s, ",", "p"): s = Replace(s, "-", "m")
    SafeName = prefix & s
End Function

' Make a plane parallel to ref at offset (mm). Returns its name.
Function MakePlane(m As Object, ref As String, ByVal off As Double, nm As String) As String
    Dim p As Object, c As Long
    m.ClearSelection2 True
    m.Extension.SelectByID2 ref, "PLANE", 0, 0, 0, False, 0, Nothing, 0
    If Abs(off) < 0.000001 Then
        Set p = m.FeatureManager.InsertRefPlane(4, 0, 0, 0, 0, 0)
    Else
        c = 8
        If off < 0 Then c = 8 + 256
        Set p = m.FeatureManager.InsertRefPlane(c, mm(Abs(off)), 0, 0, 0, 0)
    End If
    If p Is Nothing Then LogMsg "Plane failed: " & nm: MakePlane = ref: Exit Function
    m.FeatureByPositionReverse(0).Name = nm
    MakePlane = nm
    m.ClearSelection2 True
End Function

' helper plane parallel to PTop at height z (cached per part)
Function PlaneAt(m As Object, ByVal z As Double) As String
    Dim nm As String, v As Variant
    If Abs(z) < 0.000001 Then PlaneAt = "PTop": Exit Function
    nm = SafeName("Z", z)
    For Each v In PlaneList
        If v = nm Then PlaneAt = nm: Exit Function
    Next
    PlaneAt = MakePlane(m, "PTop", z, nm)
    PlaneList.Add PlaneAt
End Function

Sub MakeAxis(m As Object, p1 As String, p2 As String, nm As String)
    m.ClearSelection2 True
    m.Extension.SelectByID2 p1, "PLANE", 0, 0, 0, False, 0, Nothing, 0
    m.Extension.SelectByID2 p2, "PLANE", 0, 0, 0, True, 0, Nothing, 0
    If m.InsertAxis2(True) Then
        m.FeatureByPositionReverse(0).Name = nm
    Else
        LogMsg "Axis failed: " & nm
    End If
    m.ClearSelection2 True
End Sub

Sub BeginSketch(m As Object, plane As String)
    m.ClearSelection2 True
    m.Extension.SelectByID2 plane, "PLANE", 0, 0, 0, False, 0, Nothing, 0
    m.SketchManager.InsertSketch True
    m.SketchManager.AddToDB = True
    m.SketchManager.DisplayWhenAdded = False
End Sub

Function EndSketch(m As Object) As Object
    m.SketchManager.AddToDB = False
    m.SketchManager.DisplayWhenAdded = True
    m.SketchManager.InsertSketch True
    Set EndSketch = m.FeatureByPositionReverse(0)
End Function

Sub Ln(m As Object, x1 As Double, y1 As Double, x2 As Double, y2 As Double)
    m.SketchManager.CreateLine mm(x1), mm(y1), 0, mm(x2), mm(y2), 0
End Sub

Sub Rect(m As Object, x1 As Double, y1 As Double, x2 As Double, y2 As Double)
    Ln m, x1, y1, x2, y1: Ln m, x2, y1, x2, y2: Ln m, x2, y2, x1, y2: Ln m, x1, y2, x1, y1
End Sub

Sub Circ(m As Object, cx As Double, cy As Double, d As Double)
    m.SketchManager.CreateCircleByRadius mm(cx), mm(cy), 0, mm(d / 2)
End Sub

' boss, symmetric about the sketch plane (direction independent)
Sub ExtrudeMid(m As Object, sk As Object, depth As Double)
    Dim f As Object
    m.ClearSelection2 True
    sk.Select2 False, 0
    Set f = m.FeatureManager.FeatureExtrusion3(True, False, False, 6, 0, mm(depth), 0, False, False, False, False, _
            0, 0, False, False, False, False, True, True, True, 0, 0, False)
    If f Is Nothing Then LogMsg "Boss failed (" & m.GetTitle & ", " & sk.Name & ")"
    m.ClearSelection2 True
End Sub

' cut, symmetric about the sketch plane
Sub CutMid(m As Object, sk As Object, depth As Double)
    Dim f As Object
    m.ClearSelection2 True
    sk.Select2 False, 0
    Set f = m.FeatureManager.FeatureCut4(True, False, False, 6, 0, mm(depth), 0, False, False, False, False, _
            0, 0, False, False, False, False, False, True, True, True, True, False, 0, 0, False, False)
    If f Is Nothing Then LogMsg "Cut failed (" & m.GetTitle & ", " & sk.Name & ")"
    m.ClearSelection2 True
End Sub

' extrude everything drawn between BeginBetween/EndBoss from z0 to z1 (heights above PTop)
Function BeginBetween(m As Object, z0 As Double, z1 As Double) As String
    BeginBetween = PlaneAt(m, (z0 + z1) / 2)
    BeginSketch m, BeginBetween
End Function

Sub BossBetween(m As Object, z0 As Double, z1 As Double)
    ExtrudeMid m, EndSketch(m), z1 - z0
End Sub

Sub CutBetween(m As Object, z0 As Double, z1 As Double)
    CutMid m, EndSketch(m), z1 - z0
End Sub

Sub HidePlanes(m As Object)
    Dim v As Variant
    For Each v In PlaneList
        m.ClearSelection2 True
        If m.Extension.SelectByID2(CStr(v), "PLANE", 0, 0, 0, False, 0, Nothing, 0) Then m.BlankRefGeom
    Next
    m.ClearSelection2 True
End Sub

Function SavePart(m As Object, nm As String) As String
    Dim e As Long, w As Long, p As String
    p = OUT_DIR & nm & ".SLDPRT"
    m.ForceRebuild3 False
    m.ShowNamedView2 "*Isometric", 7
    m.ViewZoomtofit2
    If Not m.Extension.SaveAs(p, 0, 1, Nothing, e, w) Then LogMsg "Save failed: " & p & " (err " & e & ")"
    SavePart = p
End Function

'============================== gear profile ==================================
Function ACosD(ByVal x As Double) As Double
    If x >= 1 Then ACosD = 0: Exit Function
    ACosD = Atn(Sqr(1 - x * x) / x)
End Function

Function InvF(ByVal a As Double) As Double
    InvF = Tan(a) - a
End Function

Function ToothHalf(ByVal r As Double) As Double
    If r < g_rb Then r = g_rb
    ToothHalf = g_psi + InvF(g_ap) - InvF(ACosD(g_rb / r))
End Function

Sub AddPolar(ByVal r As Double, ByVal a As Double)
    gn = gn + 1
    gx(gn) = r * Cos(a): gy(gn) = r * Sin(a)
End Sub

' involute spur gear outline centred on the sketch origin
Sub DrawGear(m As Object, phaseDeg As Double)
    Const NF As Long = 7, NR As Long = 4
    Dim rp As Double, ra As Double, rf As Double, r0 As Double, p As Double, c As Double
    Dim k As Long, i As Long, r As Double, a0 As Double, a1 As Double
    rp = G_M * G_Z / 2: ra = rp + G_M: rf = rp - 1.25 * G_M
    g_ap = 20# * PI / 180#
    g_rb = rp * Cos(g_ap)
    g_psi = PI / (2 * G_Z) - BACKLASH / (2 * rp)
    p = 2 * PI / G_Z
    r0 = rf: If g_rb > r0 Then r0 = g_rb
    ReDim gx(1 To 4000): ReDim gy(1 To 4000): gn = 0
    For k = 0 To G_Z - 1
        c = phaseDeg * PI / 180# + k * p
        If rf < g_rb Then AddPolar rf, c - ToothHalf(g_rb)
        For i = 0 To NF - 1
            r = r0 + (ra - r0) * i / (NF - 1): AddPolar r, c - ToothHalf(r)
        Next
        For i = NF - 1 To 0 Step -1
            r = r0 + (ra - r0) * i / (NF - 1): AddPolar r, c + ToothHalf(r)
        Next
        If rf < g_rb Then AddPolar rf, c + ToothHalf(g_rb)
        a0 = c + ToothHalf(g_rb): a1 = c + p - ToothHalf(g_rb)
        For i = 1 To NR - 1
            AddPolar rf, a0 + (a1 - a0) * i / NR
        Next
    Next
    For i = 1 To gn
        If i < gn Then
            Ln m, gx(i), gy(i), gx(i + 1), gy(i + 1)
        Else
            Ln m, gx(i), gy(i), gx(1), gy(1)
        End If
    Next
End Sub

'============================== parts =========================================
Function BuildBase() As String
    Dim m As Object, pc As Double, top As Double, shankTop As Double
    Dim sl As Double, g0 As Double, g1 As Double, x1 As Double, x2 As Double, lockPl As String
    Set m = NewDoc(False): Set PlaneList = New Collection
    RenameDefaultPlanes m
    pc = -SV_SHAFT_OFF

    ' main block
    BeginBetween m, 0, DECK
    Rect m, BASE_X0, BASE_D0, BASE_X1, BASE_D1
    BossBetween m, 0, DECK

    ' servo pocket (drops in from the top, tabs rest on the deck)
    BeginBetween m, FLOOR_T, DECK + 5
    Rect m, -(SV_W / 2 + FIT), pc - (SV_L / 2 + FIT), SV_W / 2 + FIT, pc + (SV_L / 2 + FIT)
    CutBetween m, FLOOR_T, DECK + 5

    ' wire windows through both end walls
    BeginSketch m, "PFront"
    Rect m, -WIRE_W / 2, FLOOR_T, WIRE_W / 2, FLOOR_T + WIRE_ABOVE_FLOOR
    CutMid m, EndSketch(m), 200

    ' servo tab pilot holes (use the screws that come with the SG90)
    BeginBetween m, DECK - 6, DECK + 6
    Circ m, 0, pc - SV_TAB_HOLE_PITCH / 2, 1.8
    Circ m, 0, pc + SV_TAB_HOLE_PITCH / 2, 1.8
    CutBetween m, DECK - 6, DECK + 6

    ' dovetail groove along the whole underside (slides onto the wrist rail)
    sl = (DT_TOP - DT_NECK) / 2 / DT_H
    g0 = DT_NECK / 2 + DT_FIT - sl            ' half width at h = -1
    g1 = DT_TOP / 2 + DT_FIT + sl * 0.3       ' half width at h = DT_H + 0.3
    BeginSketch m, "PFront"
    Ln m, RAIL_X - g0, -1, RAIL_X + g0, -1
    Ln m, RAIL_X + g0, -1, RAIL_X + g1, DT_H + 0.3
    Ln m, RAIL_X + g1, DT_H + 0.3, RAIL_X - g1, DT_H + 0.3
    Ln m, RAIL_X - g1, DT_H + 0.3, RAIL_X - g0, -1
    CutMid m, EndSketch(m), 200

    ' lock-pin hole across the groove (blind on the servo side), at the base's Front plane
    x1 = RAIL_X - DT_TOP / 2 - 0.8: x2 = BASE_X1 + 2
    lockPl = MakePlane(m, "PRight", (x1 + x2) / 2, "B_LockPinPlane")
    PlaneList.Add lockPl
    BeginSketch m, lockPl
    Circ m, 0, DT_H / 2, LOCK_PIN_D
    CutMid m, EndSketch(m), x2 - x1

    ' idler pillar + friction boss + printed split snap pin
    top = GEAR_Z - PILLAR_GAP
    BeginBetween m, DECK - 0.5, top - 0.5
    Circ m, CD, 0, PILLAR_D
    BossBetween m, DECK - 0.5, top - 0.5
    BeginBetween m, top - 1, top
    Circ m, CD, 0, PILLAR_BOSS_D
    BossBetween m, top - 1, top
    shankTop = GEAR_Z + GEAR_T + 0.3
    BeginBetween m, top - 0.5, shankTop
    Circ m, CD, 0, PIN_D
    BossBetween m, top - 0.5, shankTop
    ' stepped barb (printable ramp): wide at the bottom so it hooks over the gear
    BeginBetween m, shankTop - 0.01, shankTop + 0.6
    Circ m, CD, 0, PIN_BARB_D
    BossBetween m, shankTop - 0.01, shankTop + 0.6
    BeginBetween m, shankTop + 0.59, shankTop + 1.1
    Circ m, CD, 0, (PIN_BARB_D + PIN_D) / 2 + 0.05
    BossBetween m, shankTop + 0.59, shankTop + 1.1
    BeginBetween m, shankTop + 1.09, shankTop + 1.6
    Circ m, CD, 0, PIN_D - 0.3
    BossBetween m, shankTop + 1.09, shankTop + 1.6
    ' split the pin so it can squeeze through the gear
    BeginBetween m, top - 2, shankTop + 3
    Rect m, CD - PIN_SLOT_W / 2, -10, CD + PIN_SLOT_W / 2, 10
    CutBetween m, top - 2, shankTop + 3

    ' mate references
    MakePlane m, "PTop", FLOOR_T, "B_PocketFloor"
    MakePlane m, "PTop", GEAR_Z, "B_GearPlane"
    MakePlane m, "PRight", CD, "B_IdlerX"
    MakePlane m, "PRight", RAIL_X, "B_RailX"
    MakeAxis m, "B_IdlerX", "PFront", "B_IdlerAxis"
    PlaneList.Add "B_PocketFloor": PlaneList.Add "B_GearPlane": PlaneList.Add "B_IdlerX"
    PlaneList.Add "B_RailX"
    HidePlanes m
    BuildBase = SavePart(m, "NG_Base")
End Function

Function BuildServo() As String
    Dim m As Object, pc As Double
    Set m = NewDoc(False): Set PlaneList = New Collection
    RenameDefaultPlanes m
    pc = -SV_SHAFT_OFF

    BeginBetween m, 0, SV_H
    Rect m, -SV_W / 2, pc - SV_L / 2, SV_W / 2, pc + SV_L / 2
    BossBetween m, 0, SV_H
    BeginBetween m, SV_TAB_Z, SV_TAB_Z + SV_TAB_T
    Rect m, -SV_W / 2, pc - SV_TAB_SPAN / 2, SV_W / 2, pc + SV_TAB_SPAN / 2
    BossBetween m, SV_TAB_Z, SV_TAB_Z + SV_TAB_T
    BeginBetween m, SV_TAB_Z - 1, SV_TAB_Z + SV_TAB_T + 1
    Circ m, 0, pc - SV_TAB_HOLE_PITCH / 2, SV_TAB_HOLE_D
    Circ m, 0, pc + SV_TAB_HOLE_PITCH / 2, SV_TAB_HOLE_D
    CutBetween m, SV_TAB_Z - 1, SV_TAB_Z + SV_TAB_T + 1
    BeginBetween m, SV_H - 1, SV_H + SV_BUMP_H
    Circ m, 0, 0, SV_BUMP_D
    BossBetween m, SV_H - 1, SV_H + SV_BUMP_H
    BeginBetween m, SV_H + SV_BUMP_H - 1, SV_SPLINE_TOP
    Circ m, 0, 0, SV_SPLINE_D
    BossBetween m, SV_H + SV_BUMP_H - 1, SV_SPLINE_TOP

    MakePlane m, "PTop", HORN_SEAT, "S_HornSeat"
    PlaneList.Add "S_HornSeat"
    MakeAxis m, "PFront", "PRight", "S_ShaftAxis"
    HidePlanes m
    BuildServo = SavePart(m, "NG_SG90_Dummy")
End Function

Function BuildFinger(isDriver As Boolean) As String
    Dim m As Object, s As Double, ph As Double
    Dim jx As Double, L As Double, ux As Double, uy As Double, nx As Double, ny As Double
    Dim h0 As Double, h1 As Double, ex As Double, ey As Double, ro As Double, t As Double, hh As Double
    Dim px(1 To 6) As Double, py(1 To 6) As Double, i As Long
    Set m = NewDoc(False): Set PlaneList = New Collection
    RenameDefaultPlanes m
    s = IIf(isDriver, 1#, -1#)
    ph = IIf(isDriver, 0#, 180# + 180# / G_Z)   ' idler teeth half a pitch out of phase

    ' gear
    BeginBetween m, 0, GEAR_T
    DrawGear m, ph
    BossBetween m, 0, GEAR_T

    ' finger link + jaw
    px(1) = 5.5: py(1) = -1.5
    px(2) = JAW_IN: py(2) = JAW_D0
    px(3) = JAW_IN: py(3) = JAW_D1
    px(4) = JAW_OUT: py(4) = JAW_D1
    px(5) = JAW_OUT: py(5) = JAW_D0
    px(6) = -5.5: py(6) = 1.5
    BeginBetween m, 0, GEAR_T
    For i = 1 To 6
        Ln m, s * px(i), py(i), s * px(IIf(i = 6, 1, i + 1)), py(IIf(i = 6, 1, i + 1))
    Next
    BossBetween m, 0, GEAR_T

    ' rubber-band notches on the outer face of the jaw
    BeginBetween m, -1, GEAR_T + 1
    Rect m, s * (JAW_OUT - 2), 31, s * (JAW_OUT + NOTCH_DEPTH), 34
    Rect m, s * (JAW_OUT - 2), 41, s * (JAW_OUT + NOTCH_DEPTH), 44
    CutBetween m, -1, GEAR_T + 1

    If isDriver Then
        ' horn arm pocket in the bottom face (print this face UP)
        jx = (JAW_IN + JAW_OUT) / 2: L = Sqr(jx * jx + JAW_D0 * JAW_D0)
        ux = jx / L: uy = JAW_D0 / L: nx = uy: ny = -ux
        h0 = HORN_W0 / 2 + HORN_FIT: h1 = HORN_W1 / 2 + HORN_FIT
        ex = ux * HORN_LEN: ey = uy * HORN_LEN
        BeginSketch m, "PTop"
        Ln m, -nx * h0, -ny * h0, nx * h0, ny * h0
        Ln m, nx * h0, ny * h0, ex + nx * h1, ey + ny * h1
        m.SketchManager.CreateArc mm(ex), mm(ey), 0, mm(ex + nx * h1), mm(ey + ny * h1), 0, _
                                  mm(ex - nx * h1), mm(ey - ny * h1), 0, 1
        Ln m, ex - nx * h1, ey - ny * h1, -nx * h0, -ny * h0
        CutMid m, EndSketch(m), 2 * HORN_DEPTH
        ' crush ribs: 2 each side + 1 at the tip, squeezed by the horn for a press fit
        ro = RIB_D / 2 - RIB_IN
        BeginBetween m, 0, HORN_DEPTH
        For i = 0 To 1
            t = IIf(i = 0, 0.45, 0.85)
            hh = h0 + (h1 - h0) * t
            Circ m, ux * HORN_LEN * t + nx * (hh + ro), uy * HORN_LEN * t + ny * (hh + ro), RIB_D
            Circ m, ux * HORN_LEN * t - nx * (hh + ro), uy * HORN_LEN * t - ny * (hh + ro), RIB_D
        Next
        Circ m, ux * (HORN_LEN + h1 + ro), uy * (HORN_LEN + h1 + ro), RIB_D
        BossBetween m, 0, HORN_DEPTH
        ' hub / screwdriver hole
        BeginBetween m, -1, GEAR_T + 1
        Circ m, 0, 0, HORN_HUB_D + 2 * FIT
        CutBetween m, -1, GEAR_T + 1
    Else
        BeginBetween m, -1, GEAR_T + 1
        Circ m, 0, 0, PIN_HOLE_D
        CutBetween m, -1, GEAR_T + 1
    End If

    MakeAxis m, "PFront", "PRight", "F_Axis"
    HidePlanes m
    BuildFinger = SavePart(m, IIf(isDriver, "NG_FingerDriver", "NG_FingerIdler"))
End Function

Function BuildWristMount() As String
    Dim m As Object, ro As Double, cy As Double, a As Double, ar As Double, xr As Double, k As Long
    Set m = NewDoc(False): Set PlaneList = New Collection
    RenameDefaultPlanes m
    ro = WR_RI + WR_T: cy = -WR_RI: a = WR_ANG * PI / 180#
    xr = RAIL_W / 2: ar = Atn((xr / ro) / Sqr(1 - (xr / ro) ^ 2))

    ' saddle + dovetail rail profile on the Front plane, extruded along the forearm
    BeginSketch m, "PFront"
    With m.SketchManager
        ' inner arc, left end -> right end over the top (clockwise)
        .CreateArc 0, mm(cy), 0, mm(-WR_RI * Sin(a)), mm(cy + WR_RI * Cos(a)), 0, _
                   mm(WR_RI * Sin(a)), mm(cy + WR_RI * Cos(a)), 0, -1
        ' right end cap
        .CreateLine mm(WR_RI * Sin(a)), mm(cy + WR_RI * Cos(a)), 0, mm(ro * Sin(a)), mm(cy + ro * Cos(a)), 0
        ' outer arc right end -> rail side (counter-clockwise)
        .CreateArc 0, mm(cy), 0, mm(ro * Sin(a)), mm(cy + ro * Cos(a)), 0, _
                   mm(ro * Sin(ar)), mm(cy + ro * Cos(ar)), 0, 1
    End With
    Ln m, xr, cy + ro * Cos(ar), xr, RAIL_TOP
    Ln m, xr, RAIL_TOP, DT_NECK / 2, RAIL_TOP
    Ln m, DT_NECK / 2, RAIL_TOP, DT_TOP / 2, RAIL_TOP + DT_H
    Ln m, DT_TOP / 2, RAIL_TOP + DT_H, -DT_TOP / 2, RAIL_TOP + DT_H
    Ln m, -DT_TOP / 2, RAIL_TOP + DT_H, -DT_NECK / 2, RAIL_TOP
    Ln m, -DT_NECK / 2, RAIL_TOP, -xr, RAIL_TOP
    Ln m, -xr, RAIL_TOP, -xr, cy + ro * Cos(ar)
    With m.SketchManager
        ' outer arc rail side -> left end (counter-clockwise)
        .CreateArc 0, mm(cy), 0, mm(-ro * Sin(ar)), mm(cy + ro * Cos(ar)), 0, _
                   mm(-ro * Sin(a)), mm(cy + ro * Cos(a)), 0, 1
        ' left end cap
        .CreateLine mm(-ro * Sin(a)), mm(cy + ro * Cos(a)), 0, mm(-WR_RI * Sin(a)), mm(cy + WR_RI * Cos(a)), 0
    End With
    ExtrudeMid m, EndSketch(m), WR_LEN

    ' velcro strap slots (one each side)
    BeginSketch m, "PTop"
    Rect m, STRAP_X0, -STRAP_LEN / 2, STRAP_X1, STRAP_LEN / 2
    Rect m, -STRAP_X1, -STRAP_LEN / 2, -STRAP_X0, STRAP_LEN / 2
    CutMid m, EndSketch(m), 200

    ' lock-pin cross holes through the tongue every LOCK_PITCH mm
    BeginSketch m, "PRight"
    For k = -LOCK_N To LOCK_N
        Circ m, k * LOCK_PITCH, RAIL_TOP + DT_H / 2, LOCK_PIN_D
    Next
    CutMid m, EndSketch(m), 2 * DT_TOP

    MakePlane m, "PTop", RAIL_TOP, "W_RailTop"
    PlaneList.Add "W_RailTop"
    HidePlanes m
    BuildWristMount = SavePart(m, "NG_WristMount")
End Function

'============================== assembly ======================================
Function SelEnt(asm As Object, s As String, typ As String, app As Boolean) As Boolean
    SelEnt = asm.Extension.SelectByID2(s, typ, 0, 0, 0, app, 1, Nothing, 0)
    If Not SelEnt Then LogMsg "Could not select " & typ & " " & s
End Function

Function AddMateX(asm As Object, s1 As String, t1 As String, s2 As String, t2 As String, _
                  mType As Long, flip As Boolean, d As Double, dUp As Double, dLo As Double, _
                  gNum As Double, gDen As Double, ang As Double, aUp As Double, aLo As Double, _
                  nm As String) As Boolean
    Dim e As Long, mt As Object
    asm.ClearSelection2 True
    If Not SelEnt(asm, s1, t1, False) Then Exit Function
    If Not SelEnt(asm, s2, t2, True) Then Exit Function
    Set mt = asm.AddMate5(mType, 0, flip, d, dUp, dLo, gNum, gDen, ang, aUp, aLo, False, False, 0, e)
    asm.ClearSelection2 True
    If mt Is Nothing Then Exit Function
    AddMateX = True
    Dim f As Object: Set f = LastMate(asm)
    If Not f Is Nothing Then f.Name = nm
End Function

Function LastMate(asm As Object) As Object
    Dim f As Object, s As Object
    Set f = asm.FirstFeature
    Do While Not f Is Nothing
        If f.GetTypeName2 = "MateGroup" Then Exit Do
        Set f = f.GetNextFeature
    Loop
    If f Is Nothing Then Exit Function
    Set s = f.GetFirstSubFeature
    Do While Not s Is Nothing
        Set LastMate = s
        Set s = s.GetNextSubFeature
    Loop
End Function

Function RotSign(c As Object) As Double
    Dim v As Variant
    v = c.Transform2.ArrayData        ' 3x3 rotation first; element 2 ~ sin(rotation about Y)
    RotSign = v(2)
End Function

Sub BuildAssembly(pBase As String, pServo As String, pDrv As String, pIdl As String, pWr As String)
    Dim asm As Object, e As Long, w As Long, t As String, ok As Boolean
    Dim compW As Object, compB As Object, compS As Object, compD As Object, compI As Object
    Dim sW As String, sB As String, sS As String, sDv As String, sId As String
    Dim x0 As Double, y0 As Double

    Set asm = NewDoc(True)
    asm.Extension.SaveAs OUT_DIR & "NeuroGrip_Assembly.SLDASM", 0, 1, Nothing, e, w
    t = asm.GetTitle
    If UCase(Right(t, 7)) = ".SLDASM" Then t = Left(t, Len(t) - 7)

    x0 = -RAIL_X: y0 = RAIL_TOP
    Set compW = asm.AddComponent5(pWr, 0, "", False, "", 0, 0, 0)
    Set compB = asm.AddComponent5(pBase, 0, "", False, "", mm(x0), mm(y0), 0)
    Set compS = asm.AddComponent5(pServo, 0, "", False, "", mm(x0), mm(y0 + FLOOR_T), 0)
    Set compD = asm.AddComponent5(pDrv, 0, "", False, "", mm(x0), mm(y0 + GEAR_Z), 0)
    Set compI = asm.AddComponent5(pIdl, 0, "", False, "", mm(x0 + CD), mm(y0 + GEAR_Z), 0)
    If compW Is Nothing Or compB Is Nothing Or compS Is Nothing Or compD Is Nothing Or compI Is Nothing Then
        MsgBox "Could not insert components into the assembly.", vbCritical: Exit Sub
    End If

    ' fix the wrist mount
    asm.ClearSelection2 True
    compW.Select4 False, Nothing, False
    asm.FixComponent
    asm.ClearSelection2 True

    sW = "@" & compW.Name2 & "@" & t: sB = "@" & compB.Name2 & "@" & t: sS = "@" & compS.Name2 & "@" & t
    sDv = "@" & compD.Name2 & "@" & t: sId = "@" & compI.Name2 & "@" & t

    ' base on the dovetail rail: sits on the platform, centred on the tongue, slides along it
    AddMateX asm, "PTop" & sB, "PLANE", "W_RailTop" & sW, "PLANE", 0, False, 0, 0, 0, 0, 0, 0, 0, 0, "Base_on_Rail"
    AddMateX asm, "B_RailX" & sB, "PLANE", "PRight" & sW, "PLANE", 0, False, 0, 0, 0, 0, 0, 0, 0, 0, "Base_on_Dovetail"
    ok = AddMateX(asm, "PFront" & sB, "PLANE", "PFront" & sW, "PLANE", 5, False, mm(LOCK_PITCH), mm(LOCK_N * LOCK_PITCH), 0, 0, 0, 0, 0, 0, "Slide_Limit")
    If Not ok Then
        LogMsg "Slide limit mate not supported here; used a coincident mate (suppress it to slide)."
        AddMateX asm, "PFront" & sB, "PLANE", "PFront" & sW, "PLANE", 0, False, 0, 0, 0, 0, 0, 0, 0, 0, "Slide_Position"
    End If

    ' servo in pocket
    AddMateX asm, "PTop" & sS, "PLANE", "B_PocketFloor" & sB, "PLANE", 0, False, 0, 0, 0, 0, 0, 0, 0, 0, "Servo_on_Floor"
    AddMateX asm, "PRight" & sS, "PLANE", "PRight" & sB, "PLANE", 0, False, 0, 0, 0, 0, 0, 0, 0, 0, "Servo_X"
    AddMateX asm, "PFront" & sS, "PLANE", "PFront" & sB, "PLANE", 0, False, 0, 0, 0, 0, 0, 0, 0, 0, "Servo_Z"

    ' driver finger on the servo horn
    AddMateX asm, "PTop" & sDv, "PLANE", "S_HornSeat" & sS, "PLANE", 0, False, 0, 0, 0, 0, 0, 0, 0, 0, "Driver_on_Horn"
    AddMateX asm, "F_Axis" & sDv, "AXIS", "S_ShaftAxis" & sS, "AXIS", 0, False, 0, 0, 0, 0, 0, 0, 0, 0, "Driver_Axis"

    ' idler finger on the pillar
    AddMateX asm, "PTop" & sId, "PLANE", "B_GearPlane" & sB, "PLANE", 0, False, 0, 0, 0, 0, 0, 0, 0, 0, "Idler_on_Pillar"
    AddMateX asm, "F_Axis" & sId, "AXIS", "B_IdlerAxis" & sB, "AXIS", 0, False, 0, 0, 0, 0, 0, 0, 0, 0, "Idler_Axis"

    ' gear mate 1:1 -> both fingers move equally
    If Not AddMateX(asm, "F_Axis" & sDv, "AXIS", "F_Axis" & sId, "AXIS", 10, False, 0, 0, 0, mm(CD), mm(CD), 0, 0, 0, "Gear_FingerSync") Then
        LogMsg "Gear mate failed - add it by hand: Mechanical Mates > Gear, select both F_Axis, ratio 1:1."
    End If

    ' check the gear mate turns the fingers in OPPOSITE directions; flip it if not
    Dim tmp As Boolean, sD As Double, sI As Double, gm As Object
    tmp = AddMateX(asm, "PRight" & sDv, "PLANE", "PRight" & sB, "PLANE", 6, False, 0, 0, 0, 0, 0, 20# * PI / 180#, 0, 0, "Opening_Angle")
    If tmp Then
        asm.EditRebuild3
        sD = RotSign(compD): sI = RotSign(compI)
        If Abs(sD) > 0.01 And Sgn(sD) = Sgn(sI) Then
            Set gm = asm.FeatureByName("Gear_FingerSync")
            If Not gm Is Nothing Then
                asm.ClearSelection2 True
                gm.Select2 False, 0
                asm.EditDelete
                AddMateX asm, "F_Axis" & sDv, "AXIS", "F_Axis" & sId, "AXIS", 10, True, 0, 0, 0, mm(CD), mm(CD), 0, 0, 0, "Gear_FingerSync"
                asm.EditRebuild3
                LogMsg "Gear mate direction was reversed automatically."
            End If
        End If
        ' keep the angle mate as a handy driver, but suppressed so you can drag
        Set gm = asm.FeatureByName("Opening_Angle")
        If Not gm Is Nothing Then
            asm.ClearSelection2 True
            gm.Select2 False, 0
            asm.EditSuppress2
        End If
    End If

    ' travel limit 0..OPEN_LIMIT_DEG
    If Not AddMateX(asm, "PRight" & sDv, "PLANE", "PRight" & sB, "PLANE", 6, False, 0, 0, 0, 0, 0, _
                    20# * PI / 180#, OPEN_LIMIT_DEG * PI / 180#, 0, "Opening_Limit") Then
        LogMsg "Limit angle mate not created; fingers can be dragged freely."
    End If

    asm.ClearSelection2 True
    asm.EditRebuild3
    asm.ShowNamedView2 "*Isometric", 7
    asm.ViewZoomtofit2
    asm.Extension.SaveAs OUT_DIR & "NeuroGrip_Assembly.SLDASM", 0, 1, Nothing, e, w
End Sub
