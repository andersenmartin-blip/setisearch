function export_mat2fits()
  import matlab.io.*


  ifiles = {
  'tess2019107181900-00195_045-1-1-characterized-prf.mat',...
  'tess2019107181901-00195_045-1-2-characterized-prf.mat',...
  'tess2019107181901-00195_045-1-3-characterized-prf.mat',...
  'tess2019107181901-00195_045-1-4-characterized-prf.mat',...
  'tess2019107181901-00195_045-2-1-characterized-prf.mat',...
  'tess2019107181901-00195_045-2-2-characterized-prf.mat',...
  'tess2019107181901-00195_045-2-3-characterized-prf.mat',...
  'tess2019107181901-00195_045-2-4-characterized-prf.mat',...
  'tess2019107181901-00195_045-3-1-characterized-prf.mat',...
  'tess2019107181902-00195_045-3-2-characterized-prf.mat',...
  'tess2019107181902-00195_045-3-3-characterized-prf.mat',...
  'tess2019107181902-00195_045-3-4-characterized-prf.mat',...
  'tess2019107181902-00195_045-4-1-characterized-prf.mat',...
  'tess2019107181902-00195_045-4-2-characterized-prf.mat',...
  'tess2019107181902-00195_045-4-3-characterized-prf.mat',...
  'tess2019107181902-00195_045-4-4-characterized-prf.mat'};
  timestems = {
  2019107181900,...
  2019107181901,...
  2019107181901,...
  2019107181901,...
  2019107181901,...
  2019107181901,...
  2019107181901,...
  2019107181901,...
  2019107181901,...
  2019107181902,...
  2019107181902,...
  2019107181902,...
  2019107181902,...
  2019107181902,...
  2019107181902,...
  2019107181902};

  keywords = ["TELESCOP",...
			"CTYPE1P","CUNIT1P","CRPIX1P","CRVAL1P","CDELT1P",...
			"CTYPE2P","CUNIT2P","CRPIX2P","CRVAL2P","CDELT2P"];
  for ii=1:4
    for jj=1:4
      cd(sprintf('cam%i_ccd%i',ii,jj));
      fuse = ifiles{(ii-1)*4 + jj};
      timestem = timestems{(ii-1)*4 + jj};

      load(fuse);
      for kk=1:25	       
	im = prfStruct(kk).values;
        e_im = prfStruct(kk).uncertainties;
        ccd_row = prfStruct(kk).ccdRow;
        ccd_col = prfStruct(kk).ccdColumn;
        rows    = prfStruct(kk).prfRow;
        cols    = prfStruct(kk).prfColumn;

        %create file
        f_handle = fits.createFile(sprintf('!tess%i-prf-%i-%i-row%04i-col%04i.fits',timestem,ii,jj,ccd_row,ccd_col));
        %primary image data
        fits.createImg(f_handle,'double_img',[117 117] );
        fits.writeImg(f_handle,im);
        fits.writeKey(f_handle,'ORIGIN','MIT','organization that generated this file');
        fits.writeKey(f_handle,'DATE',date(),'date that this file was generated');
        fits.writeKey(f_handle,'DATATYPE','PRF','PRF or Uncertainties');
        fits.writeKey(f_handle,'TELESCOP','TESS');
        fits.writeKey(f_handle,'VERSION','UPDATED_2.0','PRF is valid from Sector 4 and beyond');
        fits.writeKey(f_handle,'CAM',ii);
        fits.writeKey(f_handle,'CCD',jj);
        fits.writeKey(f_handle,'CCD_RREF',ccd_row,'CCD row coordinate reference of center PRF pixel');
        fits.writeKey(f_handle,'CCD_CREF',ccd_col,'CCD column reference of center PRF pixel');
        fits.writeKey(f_handle,'NSAMP',9,'Number of PRF pixels per TESS pixel');
        fits.writeKey(f_handle,'PRF_RES',2.35,'resolution of super-sampled PRF (arcseconds)');

        fits.writeKey(f_handle,'WCSNAMEP','PHYSICAL');
        fits.writeKey(f_handle,'WCSAXESP',2);
        fits.writeKey(f_handle,'CTYPE1P','RAWX');
        fits.writeKey(f_handle,'CUNIT1P','PIXEL');
        fits.writeKey(f_handle,'CRPIX1P',59);
        fits.writeKey(f_handle,'CRVAL1P',ccd_col);
        fits.writeKey(f_handle,'CDELT1P',1.0/9.0);
        fits.writeKey(f_handle,'CTYPE2P','RAWY');
        fits.writeKey(f_handle,'CUNIT2P','PIXEL');
        fits.writeKey(f_handle,'CRPIX2P',59);
        fits.writeKey(f_handle,'CRVAL2P',ccd_row);
        fits.writeKey(f_handle,'CDELT2P',1.0/9.0);

        %uncertainty data
        fits.createImg(f_handle,'double_img',[117 117]);
        fits.writeImg(f_handle,e_im);
        fits.writeKey(f_handle,'ORIGIN','MIT','organization that generated this file');
        fits.writeKey(f_handle,'DATE',date(),'date that this file was generated');
        fits.writeKey(f_handle,'DATATYPE','Uncertainties','PRF or Uncertainties');
        fits.writeKey(f_handle,'TELESCOP','TESS');
        fits.writeKey(f_handle,'CAM',ii);
        fits.writeKey(f_handle,'CCD',jj);
        fits.writeKey(f_handle,'CCD_RREF',ccd_row,'CCD row coordinate reference of center PRF pixel');
        fits.writeKey(f_handle,'CCD_CREF',ccd_col,'CCD column reference of center PRF pixel');
        fits.writeKey(f_handle,'NSAMP',9,'Number of PRF pixels per TESS pixel');
        fits.writeKey(f_handle,'PRF_RES',2.35,'resolution of super-sampled PRF (arcseconds)');
        fits.writeKey(f_handle,'WCSNAMEP','PHYSICAL');
        fits.writeKey(f_handle,'WCSAXESP',2);
        fits.writeKey(f_handle,'CTYPE1P','RAWX');
        fits.writeKey(f_handle,'CUNIT1P','PIXEL');
        fits.writeKey(f_handle,'CRPIX1P',59);
        fits.writeKey(f_handle,'CRVAL1P',ccd_col);
        fits.writeKey(f_handle,'CDELT1P',1.0/9.0);
        fits.writeKey(f_handle,'CTYPE2P','RAWY');
        fits.writeKey(f_handle,'CUNIT2P','PIXEL');
        fits.writeKey(f_handle,'CRPIX2P',59);
        fits.writeKey(f_handle,'CRVAL2P',ccd_row);
        fits.writeKey(f_handle,'CDELT2P',1.0/9.0);

        fits.closeFile(f_handle);
      end
      cd('../');
    end
  end
end




